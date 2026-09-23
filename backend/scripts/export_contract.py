"""Small exporter for the Pydantic/OpenAPI subset used here; no codegen dependency."""
import json
from pathlib import Path

from backend.app.schemas import ErrorResponse, MatchResponse, Metadata, SearchParams

ROOT = Path(__file__).resolve().parents[2]


def ts_type(schema: dict) -> str:
    if '$ref' in schema:
        return schema['$ref'].rsplit('/', 1)[-1]
    if 'const' in schema:
        return json.dumps(schema['const'], ensure_ascii=False)
    if 'enum' in schema:
        return ' | '.join(json.dumps(value, ensure_ascii=False) for value in schema['enum'])
    if 'anyOf' in schema:
        return ' | '.join(ts_type(part) for part in schema['anyOf'])
    kind = schema.get('type')
    if kind == 'array':
        return f'Array<{ts_type(schema["items"])}>'
    if kind == 'object':
        if 'properties' in schema:
            required = schema.get('required', [])
            return '{\n' + '\n'.join(f'  {key}{"" if key in required else "?"}: {ts_type(value)}'
                                     for key, value in schema['properties'].items()) + '\n}'
        return f'Record<string, {ts_type(schema["additionalProperties"])}>'
    if kind in ('string', 'boolean', 'null'):
        return kind
    if kind in ('number', 'integer'):
        return 'number'
    raise ValueError(f'Unsupported schema: {schema}')


def contract() -> str:
    schemas = {}
    for model in (SearchParams, MatchResponse, Metadata, ErrorResponse):
        schema = model.model_json_schema(mode='validation' if model is SearchParams else 'serialization')
        # Response defaults are always serialized by the API.
        if model is not SearchParams:
            schema['required'] = list(schema.get('properties', {}))
            for child in schema.get('$defs', {}).values():
                if 'properties' in child:
                    child['required'] = list(child['properties'])
        schemas.update(schema.pop('$defs', {}))
        schemas[model.__name__] = schema
    header = '// Generated from backend/app/schemas.py. Run python -m backend.scripts.export_contract.\n'
    return header + '\n\n'.join(f'export type {name} = {ts_type(schema)}' for name, schema in schemas.items()) + "\n\nexport type MatchStatus = MatchResponse['status']\n"


if __name__ == '__main__':
    (ROOT / 'frontend/src/shared/types/match.ts').write_text(contract())
