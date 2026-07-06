from __future__ import annotations

from pydantic import BaseModel, Field


class ColumnInfo(BaseModel):
    """Una columna dentro de una tabla del modelo semántico."""

    name: str = Field(..., description="Nombre de la columna, p. ej. 'ImporteTotal'")
    data_type: str = Field(..., description="Tipo de dato: 'string', 'int64', 'decimal', 'dateTime'...")
    is_key: bool = Field(default=False, description="True si la columna es clave (primaria o foránea)")


class TableInfo(BaseModel):
    """Una tabla del modelo semántico, con sus columnas."""

    name: str = Field(..., description="Nombre de la tabla, p. ej. 'Ventas'")
    table_type: str = Field(default="fact", description="'fact' (hechos) o 'dimension' (dimensión)")
    columns: list[ColumnInfo] = Field(default_factory=list, description="Columnas de la tabla")

    def column_names(self) -> list[str]:
        """Atajo útil: devuelve solo los nombres de las columnas."""
        return [c.name for c in self.columns]


class RelationshipInfo(BaseModel):
    """
    Una relación entre dos tablas.

    En Power BI las relaciones determinan cómo se propagan los filtros. Por eso
    el generador necesita conocerlas: una consulta que cruza 'Ventas' y 'Productos'
    solo funciona si existe una relación entre ambas.
    """

    from_table: str = Field(..., description="Tabla origen (lado 'muchos'), p. ej. 'Ventas'")
    from_column: str = Field(..., description="Columna clave foránea, p. ej. 'IdProducto'")
    to_table: str = Field(..., description="Tabla destino (lado 'uno'), p. ej. 'Productos'")
    to_column: str = Field(..., description="Columna clave primaria, p. ej. 'IdProducto'")
    cardinality: str = Field(default="manyToOne", description="Cardinalidad de la relación")


class MeasureInfo(BaseModel):
    """
    Una medida DAX ya definida en el modelo.

    Reutilizar medidas existentes (p. ej. [Total Ventas]) es mejor que reescribir
    el cálculo cada vez. El generador prioriza usarlas cuando la pregunta lo permite.
    """

    name: str = Field(..., description="Nombre de la medida, p. ej. 'Total Ventas'")
    expression: str = Field(..., description="Expresión DAX de la medida")
    table: str = Field(default="", description="Tabla a la que pertenece la medida")


class SchemaContext(BaseModel):
    """
    El contexto COMPLETO del modelo semántico: tablas + relaciones + medidas.

    Este es el objeto que empaqueta todo lo que un agente necesita saber sobre
    la estructura del modelo antes de generar o evaluar una consulta.
    """

    tables: list[TableInfo] = Field(default_factory=list)
    relationships: list[RelationshipInfo] = Field(default_factory=list)
    measures: list[MeasureInfo] = Field(default_factory=list)

    # ----- Métodos de conveniencia (facilitan escribir prompts y validaciones) -----

    def table_names(self) -> list[str]:
        """Lista de nombres de todas las tablas."""
        return [t.name for t in self.tables]

    def measure_names(self) -> list[str]:
        """Lista de nombres de todas las medidas."""
        return [m.name for m in self.measures]

    def get_table(self, name: str) -> TableInfo | None:
        """Busca una tabla por nombre (o None si no existe)."""
        for t in self.tables:
            if t.name.lower() == name.lower():
                return t
        return None

    def to_prompt_text(self) -> str:
        """
        Convierte el esquema a un texto legible para inyectar en el prompt del LLM.

        En vez de mandarle JSON crudo al modelo, le damos un resumen ordenado y
        compacto. Esto mejora la calidad de la generación y ahorra tokens.
        """
        lines: list[str] = ["TABLAS:"]
        for t in self.tables:
            cols = ", ".join(f"{c.name} ({c.data_type})" for c in t.columns)
            lines.append(f"  - {t.name} [{t.table_type}]: {cols}")

        lines.append("\nRELACIONES:")
        for r in self.relationships:
            lines.append(
                f"  - {r.from_table}.{r.from_column} -> {r.to_table}.{r.to_column} ({r.cardinality})"
            )

        lines.append("\nMEDIDAS:")
        for m in self.measures:
            lines.append(f"  - [{m.name}] = {m.expression}")

        return "\n".join(lines)
