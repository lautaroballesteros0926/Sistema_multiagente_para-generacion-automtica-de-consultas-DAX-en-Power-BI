from __future__ import annotations

import json
from pathlib import Path

BASELINE_PATH = Path("results/baseline.json")
SYSTEM_PATH = Path("results/system_results.json")
COMPARISON_PATH = Path("results/comparison.md")


def _delta(baseline: float, system: float) -> tuple[str, str]:
    absolute = system - baseline
    if baseline == 0:
        relative = "—" if system == 0 else "+inf%"
    else:
        relative = f"{(absolute / baseline) * 100:+.1f}%"
    return f"{absolute:+.4f}", relative


def _metric_rows(baseline: dict, system: dict) -> list[str]:
    # La línea base no tiene evaluador: no existe un ACCEPT/REJECT real ni
    # un bucle de regeneración. Se usan dos convenciones explícitas para
    # poder comparar en la misma tabla:
    #   - "% aceptadas" en la línea base = "% sintácticamente válidas"
    #     (sin evaluador, lo único que se puede afirmar de una consulta es
    #     que pasó la heurística de sintaxis).
    #   - "iteraciones promedio" en la línea base = 1.0 por definición
    #     (una sola pasada del generador, no hay bucle).
    rows = [
        ("% sintácticamente válidas", baseline["pct_syntax_valid"], system["pct_syntax_valid"]),
        ("% aceptadas (ACCEPT)", baseline["pct_syntax_valid"], system["pct_accepted"]),
        ("Iteraciones promedio", 1.0, system["avg_iterations"]),
    ]

    lines = ["| Métrica | Línea base | Sistema completo | Mejora absoluta | Mejora relativa |",
             "|---|---|---|---|---|"]
    for label, b, s in rows:
        abs_delta, rel_delta = _delta(b, s)
        lines.append(f"| {label} | {b:.4f} | {s:.4f} | {abs_delta} | {rel_delta} |")

    lines.append(f"| Score promedio del evaluador | N/A (sin evaluador) | {system['avg_score']:.4f} | — | — |")
    return lines


def _by_category_rows(baseline: dict, system: dict) -> list[str]:
    categories = sorted(set(baseline["by_category"]) | set(system["by_category"]))
    lines = [
        "| Categoría | Válidas línea base | Válidas sistema | Aceptadas sistema |",
        "|---|---|---|---|",
    ]
    for cat in categories:
        b = baseline["by_category"].get(cat, {"total": 0, "valid": 0})
        s = system["by_category"].get(cat, {"total": 0, "valid": 0, "accepted": 0})
        b_pct = f"{b['valid']}/{b['total']}"
        s_pct = f"{s['valid']}/{s['total']}"
        s_acc = f"{s.get('accepted', 0)}/{s['total']}"
        lines.append(f"| {cat} | {b_pct} | {s_pct} | {s_acc} |")
    return lines


def _errors_by_type_rows(system: dict) -> list[str]:
    errors_by_type = system.get("errors_by_type", {})
    if not errors_by_type:
        return ["| (sin errores) | 0 |"]
    return [f"| {k} | {v} |" for k, v in errors_by_type.items()]


def main() -> None:
    baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    system = json.loads(SYSTEM_PATH.read_text(encoding="utf-8"))

    lines = [
        "# Comparación: línea base vs. sistema completo",
        "",
        f"- **Línea base** (`baseline.json`): backend `{baseline['backend']}`, "
        f"{baseline['total']} preguntas, solo generador (sin evaluador, sin bucle).",
        f"- **Sistema completo** (`system_results.json`): backend `{system['backend']}`, "
        f"{system['total']} preguntas, generador + evaluador (LLM-as-a-Judge) + bucle "
        f"acotado de regeneración.",
        "",
        "> La línea base no tiene evaluador: no existe un ACCEPT/REJECT real ni un número "
        "de iteraciones real. Para poder comparar en la misma tabla se usan dos "
        "convenciones explícitas: \"% aceptadas\" en la línea base equivale a "
        "\"% sintácticamente válidas\", e \"iteraciones promedio\" en la línea base es "
        "1.0 por definición (una sola pasada, sin bucle).",
        "",
        "## Métricas globales",
        "",
        *_metric_rows(baseline, system),
        "",
        "## Por categoría (válidas / total, aceptadas / total)",
        "",
        *_by_category_rows(baseline, system),
        "",
        "## Errores por tipo (solo sistema completo, la línea base no clasifica errores)",
        "",
        "| Tipo de error | Cantidad |",
        "|---|---|",
        *_errors_by_type_rows(system),
    ]

    COMPARISON_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"Comparación guardada en {COMPARISON_PATH}")


if __name__ == "__main__":
    main()
