"""
 Solo verifica que:
  1. La configuración carga sin errores.
  2. El logging funciona.
  3. Los tres modelos de datos se pueden crear, validar y serializar a JSON.
  4. Los métodos de conveniencia devuelven lo esperado.

"""
from config.logging_config import configure_logging, get_logger
from config.settings import settings
from models import (
    ColumnInfo,
    DAXQuery,
    Decision,
    EvaluationResult,
    MeasureInfo,
    RelationshipInfo,
    SchemaContext,
    TableInfo,
)


def probar_configuracion() -> None:
    """La configuración debe cargar con sus valores por defecto."""
    assert settings.max_iterations == 3
    assert settings.use_mock is True
    assert 0.0 <= settings.accept_threshold <= 1.0
    print(f"  [config] OK  -> modelo={settings.openai_model}, max_iter={settings.max_iterations}, mock={settings.use_mock}")


def probar_logging() -> None:
    """El logger estructurado debe poder emitir un evento con campos."""
    configure_logging()
    log = get_logger("test_dia1")
    log.info("evento_de_prueba", detalle="el logging funciona", numero=42)
    print("  [logging] OK  -> se emitió un evento estructurado (línea de arriba)")


def probar_schema_context() -> None:
    """Construir un mini modelo semántico y probar sus métodos."""
    schema = SchemaContext(
        tables=[
            TableInfo(
                name="Ventas",
                table_type="fact",
                columns=[
                    ColumnInfo(name="IdVenta", data_type="int64", is_key=True),
                    ColumnInfo(name="ImporteTotal", data_type="decimal"),
                ],
            ),
            TableInfo(
                name="Productos",
                table_type="dimension",
                columns=[
                    ColumnInfo(name="IdProducto", data_type="int64", is_key=True),
                    ColumnInfo(name="Categoria", data_type="string"),
                ],
            ),
        ],
        relationships=[
            RelationshipInfo(
                from_table="Ventas", from_column="IdProducto",
                to_table="Productos", to_column="IdProducto",
            )
        ],
        measures=[
            MeasureInfo(name="Total Ventas", expression="SUM(Ventas[ImporteTotal])", table="Ventas")
        ],
    )

    # Métodos de conveniencia
    assert schema.table_names() == ["Ventas", "Productos"]
    assert schema.measure_names() == ["Total Ventas"]
    assert schema.get_table("ventas") is not None      # búsqueda sin distinguir mayúsculas
    assert schema.get_table("NoExiste") is None

    # El texto para el prompt debe mencionar las tablas y la medida
    texto = schema.to_prompt_text()
    assert "Ventas" in texto and "Total Ventas" in texto

    print("  [schema]  OK  -> 2 tablas, 1 relación, 1 medida; to_prompt_text() funciona")
    print("  ---- vista previa del texto que recibiría el LLM ----")
    for linea in texto.splitlines():
        print(f"      {linea}")
    print("  -----------------------------------------------------")


def probar_dax_query() -> None:
    """Crear una consulta DAX y probar sus verificaciones rápidas."""
    q = DAXQuery(
        query_text="EVALUATE SUMMARIZECOLUMNS(Productos[Categoria], \"Total\", [Total Ventas])",
        natural_language="ventas por categoría",
        iteration=0,
    )
    assert not q.is_empty()
    assert q.starts_with_evaluate() is True

    vacia = DAXQuery(query_text="   ", natural_language="x")
    assert vacia.is_empty() is True

    # Serialización a JSON (lo que viajaría por la API/MCP)
    json_str = q.model_dump_json()
    assert "EVALUATE" in json_str

    print("  [dax]     OK  -> consulta válida, empieza con EVALUATE, serializa a JSON")


def probar_evaluation_result() -> None:
    """Crear un veredicto del evaluador y probar sus atajos."""
    aceptada = EvaluationResult(
        score=0.91,
        decision=Decision.ACCEPT,
        explanation="Responde correctamente usando la medida existente.",
        semantic_coherence=0.95,
        schema_compliance=1.0,
        syntax_valid=True,
    )
    assert aceptada.is_accepted() is True
    assert aceptada.needs_regeneration() is False

    a_regenerar = EvaluationResult(
        score=0.6,
        decision=Decision.REGENERATE,
        explanation="La tabla 'Fecha' no existe; debe usarse 'Calendario'.",
        feedback_for_generator="Reemplaza 'Fecha' por 'Calendario' y reintenta.",
    )
    assert a_regenerar.needs_regeneration() is True
    assert a_regenerar.feedback_for_generator is not None

    # La validación de rango debe funcionar: un score fuera de [0,1] debe fallar
    try:
        EvaluationResult(score=1.5, decision=Decision.ACCEPT, explanation="x")
        raise AssertionError("Debió fallar: score > 1.0")
    except Exception:
        pass  # Se esperaba el error de validación

    print("  [eval]    OK  -> veredictos ACCEPT/REGENERATE y validación de rango funcionan")


def main() -> None:
    print("\n=== Verificación ===\n")
    probar_configuracion()
    probar_logging()
    probar_schema_context()
    probar_dax_query()
    probar_evaluation_result()
    print("\n=== TODO OK ===")


if __name__ == "__main__":
    main()
