# Comparación: línea base vs. sistema completo

- **Línea base** (`baseline.json`): backend `local:llama3.1`, 20 preguntas, solo generador (sin evaluador, sin bucle).
- **Sistema completo** (`system_results.json`): backend `gemini:gemini-flash-latest`, 20 preguntas, generador + evaluador (LLM-as-a-Judge) + bucle acotado de regeneración.

> La línea base no tiene evaluador: no existe un ACCEPT/REJECT real ni un número de iteraciones real. Para poder comparar en la misma tabla se usan dos convenciones explícitas: "% aceptadas" en la línea base equivale a "% sintácticamente válidas", e "iteraciones promedio" en la línea base es 1.0 por definición (una sola pasada, sin bucle).

## Métricas globales

| Métrica | Línea base | Sistema completo | Mejora absoluta | Mejora relativa |
|---|---|---|---|---|
| % sintácticamente válidas | 1.0000 | 0.9500 | -0.0500 | -5.0% |
| % aceptadas (ACCEPT) | 1.0000 | 0.7500 | -0.2500 | -25.0% |
| Iteraciones promedio | 1.0000 | 1.4000 | +0.4000 | +40.0% |
| Score promedio del evaluador | N/A (sin evaluador) | 0.7700 | — | — |

## Por categoría (válidas / total, aceptadas / total)

| Categoría | Válidas línea base | Válidas sistema | Aceptadas sistema |
|---|---|---|---|
| agregacion_con_filtro | 4/4 | 4/4 | 4/4 |
| agregacion_simple | 4/4 | 4/4 | 3/4 |
| cruce_tablas | 4/4 | 3/4 | 1/4 |
| inteligencia_temporal | 4/4 | 4/4 | 4/4 |
| reutilizacion_medidas | 4/4 | 4/4 | 3/4 |

## Errores por tipo (solo sistema completo, la línea base no clasifica errores)

| Tipo de error | Cantidad |
|---|---|
| fallo_parseo_evaluador | 1 |
| rechazado_por_evaluador | 3 |
| sintaxis_invalida | 1 |