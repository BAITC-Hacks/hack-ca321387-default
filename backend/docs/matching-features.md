# Серверные возможности подбора EventLens

## Совместимость и границы

Изменения этой задачи находятся только в `backend/`. Старые модели
`SearchParams`, `MatchResponse`, `Contractor`, `DiagnosticStep` и обычный
`POST /api/match` сохранены: те же статусы, ключи, значения, округление и порядок.
Существующие frontend-fixtures и генератор TypeScript используются тестами
только для чтения. Генераторы, записывающие во frontend, запускать для этих
возможностей не требуется.

Ранее были реализованы Evidence Ledger, значения и веса компонентов рейтинга,
последовательная воронка, подсказка бюджета с повторной проверкой и даты ±2 дня.
Теперь дополнительно доступны точные вклады, признаки неприменённых фильтров,
сравнение, произвольное ограниченное окно дат, проверенные пресеты и opt-in trace.

| API | Запрос | Ответ |
| --- | --- | --- |
| `POST /api/match` | прежний `SearchParams` | прежний `MatchResponse`, без новых полей |
| `POST /api/match/details` | тот же `SearchParams` | `DetailedMatchResponse` |
| `POST /api/availability` | `AvailabilityRequest` | `AvailabilityResponse` |
| `GET /api/demo-presets` | без параметров | `DemoPresetsResponse` |
| `POST /api/debug/match` | тот же `SearchParams` | `DebugMatchResponse`, только при `ENABLE_MATCH_TRACE=true` |

Справочники и готовность сервера остаются на `/api/meta/options` и `/api/health`.
Точные схемы публикуются в `/openapi.json` и `/docs`. Новые схемы находятся в
`app/feature_schemas.py` и `app/discovery.py`, старые — в `app/schemas.py`.

## Общий pipeline и данные

`MatchingService.match`, `.details` и `.debug_match` вызывают один `_execute`.
Детали собираются из сохранённых исходных вычислений этого исполнения. Trace не
запускает второй подбор и не обращается повторно к ML для объяснения результата.
`rules.evaluate` остаётся единственным источником предикатов и evidence.
`find_availability` и пресеты используют `filter_profiles`, без ранжирования ML.

Каталог загружается при старте. В текущем CSV 66 профилей, из них 13 синтетических;
версия снимка `87d082de8481f637`. Неизвестный календарь (`busy_dates=None`) не
подтверждает доступность; известный пустой календарь означает отсутствие занятых
дат внутри покрытия. Покрытие включительно: **2026-09-23 — 2026-12-31**.

Цена — стартовая стоимость **за мероприятие в KZT**, не почасовая ставка и не
окончательная смета. Длительность — часы присутствия. `max_hours=null` для
документированных услуг без присутствия означает `not_applicable`, для других
неизвестных лимитов — `unknown`. Запрошенный неизвестный лимит исключает профиль.
Язык/длительность, отсутствующие в запросе, не превращаются в подтверждённое
совпадение. Признаки происхождения передаются из данных и не влияют на рейтинг.

## 1. Evidence и точные составляющие score

Обычный запрос, пригодный для обоих маршрутов поиска:

```json
{
  "city": "Алматы",
  "date": "2026-11-18",
  "event_type": "корпоратив",
  "category": "Ведущий",
  "budget": 1000000,
  "language": "русский",
  "duration": 6
}
```

Обязательны первые пять полей. Бюджет — конечное положительное число до
100 000 000 включительно; duration — целое 1–12 или null. Необязательные
поля можно опустить. Даты — календарные строки `YYYY-MM-DD`, не timestamps.

`POST /api/match/details` возвращает:

```text
query       нормализованный запрос
match       прежний MatchResponse целиком, без преобразования порядка/значений
ranking[]   точная декомпозиция для каждого фактически показанного профиля
funnel[]    расширенная воронка из тех же шагов
comparison  единицы измерения и проверяемые причины порядка
```

Жёсткие условия находятся отдельно в `match.results[].evidence`: `category`,
`city`, `date`, `format`, `budget`, `language`, `duration`. Используются прежние
`matched`, `code`, `source_field`, `requested`, `actual`, `reason`. Семантический
объект — сигнал близости, а не обязательная проверка.

В `ranking[]` есть `candidate_id`, позиция 1–3, `score`, шкала 0–1,
`interpretation="fit_not_probability"`, `decomposition="weighted_sum"`,
`components[]`, `unrounded_score`, `rounding_adjustment`, `rounding`.

Каждый компонент содержит:

- `component`: semantic / lexical / budget / duration;
- `state`: active / not_requested / not_applicable / unavailable;
- `value`, `weight`, `contribution`: исходные числа **до округления** либо null;
- `source_fields` и `reason`: реальные источники и метод вычисления.

Формула и веса **не изменены**:

- semantic: TF-IDF cosine от существующего сервиса;
- lexical: Jaccard от существующего сервиса;
- budget: `clamp(1 - price / budget, 0, 1)`;
- duration: `clamp((max_hours - duration) / duration, 0, 1)`, только если применимо;
- с длительностью веса `.50 / .20 / .20 / .10`;
- без неё `.60 / .20 / .20`, duration исключён;
- недоступные компоненты исключены, оставшиеся веса перенормированы.

Для active-компонента `contribution=value*weight`. Для остальных значение,
вес и вклад — null; это отсутствие компонента, а не вычисленный ноль.
Суммируются только известные вклады в фиксированном порядке semantic, lexical,
budget, duration. Сумма равна `unrounded_score` в точности вычислений IEEE-754;
публичный `score=round(unrounded_score,6)` по Python. Разность
`score-unrounded_score` явно передаётся как `rounding_adjustment`.
Сумма вкладов плюс эта поправка восстанавливает публичный score с погрешностью
чисел с плавающей точкой. Старый округлённый `score_breakdown` не используется
для восстановления исходных вычислений.

Реальный фрагмент ответа для примера выше при `SEMANTIC_MODE=disabled`:

```json
{
  "candidate_id": "HK-44923",
  "position": 1,
  "score": 0.344444,
  "unrounded_score": 0.34444444444444444,
  "rounding_adjustment": -4.4444444446956055e-7,
  "components": [
    {"component":"semantic","state":"unavailable","value":null,"weight":null,"contribution":null},
    {"component":"lexical","state":"unavailable","value":null,"weight":null,"contribution":null},
    {"component":"budget","state":"active","value":0.35,"weight":0.6666666666666666,"contribution":0.2333333333333333},
    {"component":"duration","state":"active","value":0.3333333333333333,"weight":0.3333333333333333,"contribution":0.1111111111111111}
  ]
}
```

В фрагменте опущены текстовые пояснения и метаданные шкалы. При включённом ML
цифры могут отличаться; режим и версия алгоритма указаны в `match.model_info`.
ML сейчас возвращает два текстовых сигнала, а итоговая аддитивная формула
известна backend. Отдельный ML-контракт не менялся. Ответ иной формы считается
недоступностью зависимости; не выдумывается декомпозиция неизвестной модели.

## 2. Constraint Funnel

Порядок сохранён: **category → city → date → format → budget → language → duration**.
Каждый расширенный шаг имеет прежние `stage`, `label`, `before`, `after`,
`excluded`, `count` (alias after), а также `application` и `reason`.
Отсутствующие язык/длительность помечаются `not_requested`; счётчики не меняются.
`applied` означает, что условие задано: для отдельных услуг оно может быть N/A,
что видно в их evidence, и это не подтверждённый положительный факт.

Реальный первый шаг указанного запроса:

```json
{"stage":"category","label":"В категории","before":66,"after":15,"excluded":51,"count":15,"application":"applied","reason":"Применён общий предикат отбора; неприменимые для услуги значения не подтверждают совпадение."}
```

Следующий before равен предыдущему after; итог воронки — число **всех**
допущенных к ранжированию, а не длина выдачи (пример: 4 допущено, 3 показано).
Первый нулевой этап зависит от порядка. Сам по себе он не доказывает, что
изменение только этого условия даст совпадение. Существующая бюджетная подсказка
по-прежнему рассчитывается отдельной проверкой всех остальных условий.

## 3. Alternative Dates

Относительное окно (null или отсутствие offsets означает 2 дня в эту сторону):

```json
{
  "query": {"city":"Алматы","date":"2026-11-18","event_type":"корпоратив","category":"Ведущий","budget":1000000,"language":"русский","duration":6},
  "days_before": 3,
  "days_after": 3
}
```

Либо тот же `query` плюс `date_from` и `date_to`. Оба края обязательны,
если задан хотя бы один. Смешивать явный диапазон и заданные числом offsets нельзя
(нулевое числовое значение тоже считается заданным offset; null — отсутствующим).
Offsets — целые 0–30, всё запрошенное окно — максимум **31 день включительно**.
Проверка лимита выполняется до обрезки относительного окна.

Явный диапазон за пределами покрытия, обратный диапазон, timestamp вместо даты,
слишком длинное окно — HTTP 422 с обычным `ErrorResponse`. Относительное окно
обрезается по покрытию. Часовых поясов и преобразования дня через UTC здесь нет.

Ответ содержит нормализованный `query`, фактические `date_from`/`date_to`,
`days: [{date,available}]`, `recommended_date`, `data_version`.
Для примера выше реальный фрагмент ответа:

```json
{
  "date_from":"2026-11-15",
  "date_to":"2026-11-21",
  "days":[
    {"date":"2026-11-15","available":5},
    {"date":"2026-11-16","available":3},
    {"date":"2026-11-17","available":3},
    {"date":"2026-11-18","available":4},
    {"date":"2026-11-19","available":4},
    {"date":"2026-11-20","available":2},
    {"date":"2026-11-21","available":5}
  ],
  "recommended_date":"2026-11-15",
  "data_version":"87d082de8481f637"
}
```

На каждом дне сохраняются все условия, кроме даты. ML не вызывается.
Рекомендация выбирается среди **других** проверенных дат с положительным числом
вариантов: больше кандидатов → ближе к query.date → более ранняя дата.
Если альтернатив нет (включая окно из одного выбранного дня), рекомендация null,
а проверенные дни с нулевыми счётчиками остаются в ответе.
Для повторного поиска достаточно скопировать ответный query, заменить date
выбранным днём и отправить обычный `/api/match`.

## 4. Compare Top-3

Отдельный маршрут сравнения не нужен. `/api/match/details` возвращает
`comparison.candidate_ids` в том же порядке, что `match.results`.
Имена, цены, языки, длительности, synthetic, score, explanations и проверки
переиспользуются из этих карточек; профили не дублируются вторым набором.

Дополнительно предоставлены:

- `currency=KZT`, `price_unit=event`, `price_basis=starting_price`;
- `duration_unit=hours`, пояснения о сопоставимости и неизвестном составе пакетов;
- `formats`: отображение ID → подтверждённые форматы из структурированного evidence;
- `ordering=[score_desc,price_asc,id_asc]`;
- `decisions[]`: объяснение для каждой пары среди фактически показанных карточек.

Пара содержит higher_id/lower_id, decided_by (`score`, `price`, `id`),
разность **округлённых** score, `contribution_deltas` известных вкладов и reason.
Когда хотя бы один вклад неизвестен, его разность null. Эти разности описывают
входы формулы; deciding factor учитывает именно старый порядок с округлением.
Равные score разрешаются ценой, затем ID. Победа по ID не трактуется как качество.
Величины duration сравнимы только для известных лимитов присутствия, а N/A не
означает ноль часов. `synthetic` берётся только из профиля.

При 0/1/2/3 результатах возвращается именно столько ID и ranking-объектов.
При 0 или 1 карточке `decisions=[]`. Неподходящие кандидаты не добавляются.

## 5. Demo Presets

`GET /api/demo-presets` возвращает `data_version`, `presets[]`, `omitted[]`.
У пресета стабильный id, title, description, query, expected_status,
проверенный eligible_count, а также nullable related_query/related_eligible_count.
Это **запросы**, а не заготовленные ответы: клиент отправляет выбранный query
в обычный matching API.

Пресеты строятся из реально наблюдаемых сочетаний город/категория/формат и цен,
проверяются общими фильтрами и сохраняются на время жизни неизменяемого снимка.
Замена объекта каталога/перезапуск с новым CSV инвалидирует кэш. Содержимое
запросов и числа могут измениться с данными; стабильными остаются ID сценариев.

Текущий снимок подтверждает:

| ID | Параметры (язык и длительность null) | Допущено |
| --- | --- | --- |
| normal_match | Алматы, Ведущий, корпоратив, 2026-09-23, 2 000 000 ₸ | 5 |
| strict_budget | те же условия, бюджет 325 000 ₸ | 0; related_query даёт 5 |
| date_effect | те же условия и 2 000 000 ₸, 2026-09-24 | 4; related_query на 2026-09-23 даёт 5 |
| rare_category | Алматы, Ведущий церемонии, свадьба, 2026-09-23, 250 000 ₸ | 1 |

Редкая категория выбирается из категорий с меньшим числом профилей, чем у самой
частой; сначала рассматривается самая малочисленная. Дата-демонстрация требует
реального изменения числа допущенных на соседних днях. Если снимок не позволяет
получить сценарий, он отсутствует в presets и указан в omitted с причиной.
Невалидные запросы не используются для демонстрации пустой выдачи.

## 6. Backend Match Trace

По умолчанию `/api/debug/match` отсутствует и возвращает стандартный **404**,
включая отсутствие в OpenAPI. Включение при создании приложения:

```bash
ENABLE_MATCH_TRACE=true PYTHONDONTWRITEBYTECODE=1 \
  backend/.venv/bin/python -m uvicorn backend.app.main:app --port 8000
```

Используется существующая конфигурация через environment. Отдельная авторизация
не добавлялась; включённый маршрут предназначен для контролируемой среды демо
или разработки, а не для публичного production-доступа.

Ответ: `{details: DetailedMatchResponse, trace: MatchTrace}`. Details и обычный
match получены из одного исполнения. Trace содержит:

- UUID request_id и нормализованный запрос;
- catalog_count, total_eligible, returned_count и фактический model_info;
- измеренные stages с elapsed_ms и nullable before/after;
- total_ms, timing_scope и notices с безопасными кодами и сообщениями.

Этапы: query.normalize, constraints.evaluate, filter.category/city/date/format/
budget/language/duration, diagnostics.summarize, alternatives.budget (только когда
он выполнялся), alternatives.dates, ranking.semantic (только при вызове сервиса),
ranking.score_and_sort, response.assemble, details.assemble.
Предикаты предварительно вычисляются общим evaluate: эта стоимость измеряется
в constraints.evaluate. filter.* измеряют фактическое последовательное применение
сохранённых проверок. Вызовы фильтров для альтернатив измеряются отдельно общей
длительностью соответствующего alternatives-этапа и не подменяют основную воронку.

Время — монотонный perf_counter_ns; total включает pipeline и сборку details,
но исключает HTTP-парсинг/валидацию тела, сериализацию ответа и передачу по сети.
Небольшая разница между суммой этапов и total — реальная стоимость orchestration.
UUID и времена меняются между вызовами; результат поиска, evidence и score
детерминированы при тех же query, data_version и режиме алгоритма.

Существующая обработка ML сохранена: timeout, недоступность и невалидный ответ
дают fallback с null текстовыми компонентами и перенормированными весами.
Trace дополнительно различает semantic_timeout, semantic_unreachable,
semantic_invalid_response, semantic_disabled, semantic_not_used, text_score_missing.
Не передаются URL сервиса, exception text, токены, embeddings или stack traces.
Ошибка валидации остаётся 422, ошибка каталога — 503, неожиданная ошибка — 500;
они не маскируются успешным trace.

## Запуск и проверки

Из корня репозитория, без изменения зависимостей:

```bash
# Установленные backend/.venv и requirements-dev.txt используются как раньше.
PYTHONDONTWRITEBYTECODE=1 backend/.venv/bin/python -m uvicorn backend.app.main:app --port 8000
# При необходимости отдельным процессом запускается существующий неизменённый ML:
PYTHONDONTWRITEBYTECODE=1 backend/.venv/bin/python -m uvicorn app.main:app --app-dir services/ai --port 8100

PYTHONDONTWRITEBYTECODE=1 backend/.venv/bin/python -m unittest discover -s backend/tests -v
PYTHONDONTWRITEBYTECODE=1 backend/.venv/bin/python -m mypy --cache-dir backend/.mypy_cache --strict backend/app
PYTHONDONTWRITEBYTECODE=1 backend/.venv/bin/python -m compileall -q backend/app
PYTHONDONTWRITEBYTECODE=1 backend/.venv/bin/python -m backend.scripts.http_smoke
```

Внутри `backend/.env.example` перечислены серверные переменные. Uvicorn может
прочитать локальную копию через `--env-file backend/.env`. Новый флаг только один:
`ENABLE_MATCH_TRACE=false` по умолчанию. Путь к CSV, CORS, AI URL/таймаут и
SEMANTIC_MODE остаются прежними.

Примеры HTTP:

```bash
curl http://localhost:8000/api/demo-presets
curl -X POST http://localhost:8000/api/match/details \
  -H 'Content-Type: application/json' \
  -d '{"city":"Алматы","date":"2026-11-18","event_type":"корпоратив","category":"Ведущий","budget":1000000,"language":"русский","duration":6}'
curl -X POST http://localhost:8000/api/availability \
  -H 'Content-Type: application/json' \
  -d '{"query":{"city":"Алматы","date":"2026-11-18","event_type":"корпоратив","category":"Ведущий","budget":1000000,"language":"русский","duration":6},"days_before":3,"days_after":3}'
# После явного включения trace тот же SearchParams отправляется на /api/debug/match.
```

Новые тесты проверяют точность вкладов (включая границы округления), tie-break,
неизвестные значения, no-op фильтры, единственное исполнение pipeline/ML, trace
off/on, все календарные ограничения, отсутствие ML при подсчётах, актуальность
пресетов и их кэша. Существующий тест сравнивает прежние ответы и TypeScript
контракт с файлами frontend без их изменения. HTTP smoke поднимает настоящий
backend и неизменённый AI-сервис, проверяет старый и новые маршруты, затем
останавливает AI и проверяет fallback и trace. Python-кэш у subprocess отключён,
поэтому сервис не создаёт файлы вне backend.

Frontend-команды и браузерные проверки не входят в этот backend-only прогон.
Для использования новых данных нужны отдельные клиентские интеграции; прежний
frontend продолжает работать с `/api/match` без обновления.
