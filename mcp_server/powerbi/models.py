from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ValidationResult(BaseModel):
    """Resultado de validar la sintaxis de una consulta DAX."""

    valid: bool
    error: str | None = None


class ExecutionResult(BaseModel):
    """Resultado de ejecutar una consulta DAX contra el modelo semántico."""

    rows: list[dict[str, Any]] = Field(default_factory=list)
    row_count: int = 0
    truncated: bool = False
    error: str | None = None
