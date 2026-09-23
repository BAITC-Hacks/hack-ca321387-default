import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from collections.abc import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from .catalog import Catalog, CatalogError, DEFAULT_DATASET, UnknownOption, load_catalog
from .matching import MatchingService
from .schemas import ErrorResponse, FieldError, MatchResponse, Metadata, SearchParams
from .semantic import HttpSemanticProvider, SemanticProvider

logger = logging.getLogger(__name__)


def create_app(catalog: Catalog | None = None, semantic: SemanticProvider | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        try:
            snapshot = catalog or load_catalog(Path(os.getenv('DATASET_PATH', str(DEFAULT_DATASET))))
            mode = os.getenv('SEMANTIC_MODE', 'tfidf')
            if mode not in ('tfidf', 'disabled'):
                raise ValueError('SEMANTIC_MODE must be tfidf or disabled')
            provider = semantic
            if provider is None and mode == 'tfidf':
                provider = HttpSemanticProvider(os.getenv('AI_SERVICE_URL', 'http://localhost:8100'),
                                                float(os.getenv('AI_TIMEOUT_SECONDS', '2')))
            application.state.matching = MatchingService(snapshot, provider)
        except CatalogError:
            logger.exception('Catalog initialization failed')
            application.state.matching = None
        yield

    app = FastAPI(title='EventLens API', version='2.0.0', lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[value.strip() for value in os.getenv('CORS_ORIGINS', 'http://localhost:3000,http://localhost:5173').split(',')],
        allow_credentials=False, allow_methods=['GET', 'POST'], allow_headers=['Content-Type'],
    )

    def service() -> MatchingService:
        instance: MatchingService | None = app.state.matching
        if instance is None:
            raise CatalogError('Каталог временно недоступен')
        return instance

    def error(status: int, code: str, message: str, detail: list[FieldError] | None = None) -> JSONResponse:
        return JSONResponse(status_code=status, content=ErrorResponse(code=code, message=message, detail=detail or []).model_dump())

    @app.exception_handler(RequestValidationError)
    async def invalid_request(_request: Request, exc: RequestValidationError) -> JSONResponse:
        messages = {
            'city': 'Выберите город из справочника.', 'category': 'Выберите категорию из справочника.',
            'event_type': 'Выберите формат из справочника.', 'language': 'Выберите язык или «Не важно».',
            'date': 'Укажите дату YYYY-MM-DD с 2026-09-23 по 2026-12-31.',
            'budget': 'Бюджет должен быть конечным числом больше 0 и не больше 100 000 000 ₸.',
            'duration': 'Длительность должна быть целым числом от 1 до 12 или null.',
        }
        fields = []
        for item in exc.errors():
            field = '.'.join(str(part) for part in item['loc'][1:]) or None
            message = messages.get(field or '', 'Некорректная структура запроса.')
            fields.append(FieldError(field=field, code=item['type'], message=message))
        return error(422, 'validation_error', 'Проверьте параметры поиска.', fields)

    @app.exception_handler(UnknownOption)
    async def unknown_option(_request: Request, exc: UnknownOption) -> JSONResponse:
        return error(422, 'unknown_option', str(exc), [FieldError(field=exc.field, code='unknown_option', message=str(exc))])

    @app.exception_handler(CatalogError)
    async def unavailable(_request: Request, _exc: CatalogError) -> JSONResponse:
        return error(503, 'catalog_unavailable', 'Каталог подрядчиков временно недоступен. Попробуйте ещё раз.')

    @app.exception_handler(HTTPException)
    async def http_error(_request: Request, exc: HTTPException) -> JSONResponse:
        return error(exc.status_code, 'route_not_found' if exc.status_code == 404 else 'http_error',
                     'Маршрут не найден.' if exc.status_code == 404 else 'Запрос не поддерживается.')

    @app.exception_handler(Exception)
    async def unexpected(_request: Request, exc: Exception) -> JSONResponse:
        logger.error('Unhandled API error', exc_info=exc)
        return error(500, 'internal_error', 'Внутренняя ошибка сервиса. Попробуйте ещё раз.')

    errors: dict[int | str, dict[str, object]] = {422: {'model': ErrorResponse}, 503: {'model': ErrorResponse}, 500: {'model': ErrorResponse}}

    @app.get('/api/health', responses={503: {'model': ErrorResponse}})
    def health() -> dict[str, str]:
        return {'status': 'ok', 'service': 'EventLens API', 'data_version': service().catalog.version}

    @app.get('/api/architecture')
    def architecture() -> dict[str, str]:
        return {'frontend': 'React + Vite', 'backend': 'FastAPI', 'ai_service': 'batch text similarity'}

    @app.get('/api/meta/options', response_model=Metadata, responses=errors)
    def metadata() -> Metadata:
        return service().catalog.metadata()

    @app.post('/api/match', response_model=MatchResponse, responses=errors)
    def match(query: SearchParams) -> MatchResponse:
        # Sync handler runs in FastAPI's thread pool, including the bounded AI call.
        return service().match(query)

    return app


app = create_app()
