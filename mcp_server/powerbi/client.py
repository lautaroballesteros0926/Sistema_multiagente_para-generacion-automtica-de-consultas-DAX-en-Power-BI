from __future__ import annotations

import json
import random
import re
from pathlib import Path
from typing import Any

from config.settings import settings
from models import SchemaContext
from mcp_server.powerbi.models import ExecutionResult, ValidationResult

# Tabla[Columna] pegado, sin espacio: distingue una referencia de columna real
# de una medida entre corchetes como [Total Ventas].
_COLUMN_REF = re.compile(r"(\w+)\[(\w+)\]")
# [Nombre de medida]: corchetes NO precedidos por un carácter de palabra.
_MEASURE_REF = re.compile(r"(?<!\w)\[([^\[\]]+)\]")

_MOCK_ROW_COUNT = 5


class PowerBIClient:
    """
    Cliente hacia el modelo semántico de Power BI.

    En modo mock (use_mock=True) todo se resuelve contra `mock_schema.json` y
    una validación/ejecución heurística, sin depender de credenciales ni de
    una instancia real de Power BI. En modo real, cada método delega en
    azure-identity + XMLA (no implementado todavía).
    """

    def __init__(self, use_mock: bool = settings.use_mock) -> None:
        self.use_mock = use_mock
        self._schema_cache: SchemaContext | None = None

    async def fetch_schema(self) -> SchemaContext:
        if not self.use_mock:
            raise NotImplementedError("Configura credenciales Azure en .env")

        if self._schema_cache is None:
            path = Path(settings.mock_schema_path)
            data = json.loads(path.read_text(encoding="utf-8"))
            self._schema_cache = SchemaContext.model_validate(data)
        return self._schema_cache

    async def fetch_tables(self) -> list[dict]:
        schema = await self.fetch_schema()
        return [t.model_dump() for t in schema.tables]

    async def fetch_relationships(self) -> list[dict]:
        schema = await self.fetch_schema()
        return [r.model_dump() for r in schema.relationships]

    async def fetch_measures(self) -> list[dict]:
        schema = await self.fetch_schema()
        return [m.model_dump() for m in schema.measures]

    async def validate_dax(self, query: str) -> dict:
        if not self.use_mock:
            raise NotImplementedError("Configura credenciales Azure en .env")

        schema = await self.fetch_schema()
        result = self._validate_heuristic(query, schema)
        return result.model_dump()

    async def execute_query(self, query: str, max_rows: int = 100) -> dict:
        if not self.use_mock:
            raise NotImplementedError("Configura credenciales Azure en .env")

        schema = await self.fetch_schema()
        validation = self._validate_heuristic(query, schema)
        if not validation.valid:
            return ExecutionResult(error=validation.error).model_dump()

        result = self._fabricate_rows(query, schema, max_rows)
        return result.model_dump()

    def _validate_heuristic(self, query: str, schema: SchemaContext) -> ValidationResult:
        text = query.strip()

        if not text.upper().startswith("EVALUATE"):
            return ValidationResult(valid=False, error="La consulta debe comenzar con EVALUATE")

        if text.count("(") != text.count(")"):
            return ValidationResult(valid=False, error="Paréntesis desbalanceados")

        if text.count("[") != text.count("]"):
            return ValidationResult(valid=False, error="Corchetes desbalanceados")

        for table_name, _column_name in _COLUMN_REF.findall(text):
            if schema.get_table(table_name) is None:
                return ValidationResult(
                    valid=False,
                    error=f"La tabla '{table_name}' no existe en el esquema",
                )

        return ValidationResult(valid=True)

    def _fabricate_rows(self, query: str, schema: SchemaContext, max_rows: int) -> ExecutionResult:
        column_refs = _COLUMN_REF.findall(query)
        measure_refs = [name for name in _MEASURE_REF.findall(query) if name not in {t for t, _ in column_refs}]

        row_count = min(max_rows, _MOCK_ROW_COUNT)
        rng = random.Random(hash(query) & 0xFFFFFFFF)

        rows: list[dict[str, Any]] = []
        for i in range(row_count):
            row: dict[str, Any] = {}
            for table_name, column_name in column_refs:
                table = schema.get_table(table_name)
                data_type = "string"
                if table is not None:
                    for col in table.columns:
                        if col.name.lower() == column_name.lower():
                            data_type = col.data_type
                            break
                row[f"{table_name}[{column_name}]"] = self._fabricate_value(data_type, rng, i)

            for measure_name in measure_refs:
                row[f"[{measure_name}]"] = round(rng.uniform(100, 50000), 2)

            rows.append(row)

        return ExecutionResult(
            rows=rows,
            row_count=len(rows),
            truncated=_MOCK_ROW_COUNT > max_rows,
        )

    @staticmethod
    def _fabricate_value(data_type: str, rng: random.Random, row_idx: int) -> Any:
        if data_type == "int64":
            return row_idx + 1
        if data_type == "decimal":
            return round(rng.uniform(10, 5000), 2)
        if data_type == "dateTime":
            return f"2024-{(row_idx % 12) + 1:02d}-01"
        return f"Valor {row_idx + 1}"


# Instancia única compartida por las herramientas MCP (mismo patrón que `settings`).
client = PowerBIClient()
