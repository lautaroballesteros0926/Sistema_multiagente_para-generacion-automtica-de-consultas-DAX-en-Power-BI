from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from pathlib import Path

from config.logging_config import configure_logging, get_logger
from config.settings import settings
from models import Decision
from orchestrator.graph import aclose_agents, build_graph
from orchestrator.state import AgentState

CORPUS_PATH = Path("tests/fixtures/corpus.json")
RESULTS_PATH = Path("results/system_results.json")

JSON_PARSE_FAILURE_MARKER = "JSON válido"

log = get_logger(__name__)


def _backend_label() -> str:
    if settings.gemini_api_key:
        return f"gemini:{settings.generator_model}"
    return f"local:{settings.local_model}"


def _classify_error(final_result: dict) -> str | None:
    """Clasifica por qué una pregunta no terminó en ACCEPT (None si sí)."""
    if final_result["decision"] == Decision.ACCEPT.value:
        return None
    if not final_result["syntax_valid"]:
        return "sintaxis_invalida"
    if JSON_PARSE_FAILURE_MARKER in final_result["explanation"]:
        return "fallo_parseo_evaluador"
    return "rechazado_por_evaluador"


async def main() -> None:
    configure_logging()
    corpus = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))

    graph = build_graph()
    per_question = []
    by_category: dict[str, dict[str, int]] = defaultdict(lambda: {"total": 0, "valid": 0, "accepted": 0})
    errors_by_type: dict[str, int] = defaultdict(int)

    try:
        for item in corpus:
            initial_state: AgentState = {
                "question": item["question"],
                "dax_query": None,
                "evaluation": None,
                "iteration": 0,
                "max_iterations": settings.max_iterations,
                "final_result": None,
            }

            try:
                final_state = await asyncio.wait_for(graph.ainvoke(initial_state), timeout=480)
                final_result = dict(final_state["final_result"])
                final_result["decision"] = final_result["decision"].value
            except Exception as exc:
                log.warning("pregunta_fallo_infraestructura", id=item["id"], error=str(exc))
                final_result = {
                    "dax": "",
                    "score": 0.0,
                    "decision": Decision.REJECT.value,
                    "iterations": 0,
                    "syntax_valid": False,
                    "explanation": f"Fallo de infraestructura, ningún backend respondió: {exc}",
                }

            valid = bool(final_result["syntax_valid"])
            accepted = final_result["decision"] == Decision.ACCEPT.value
            if final_result["dax"] == "":
                error_type = "fallo_infraestructura"
            else:
                error_type = _classify_error(final_result)

            by_category[item["category"]]["total"] += 1
            if valid:
                by_category[item["category"]]["valid"] += 1
            if accepted:
                by_category[item["category"]]["accepted"] += 1
            if error_type is not None:
                errors_by_type[error_type] += 1

            per_question.append({
                "id": item["id"],
                "category": item["category"],
                "dax": final_result["dax"],
                "score": final_result["score"],
                "decision": final_result["decision"],
                "iterations": final_result["iterations"],
                "syntax_valid": valid,
                "explanation": final_result["explanation"],
                "error_type": error_type,
            })
            log.info(
                "pregunta_procesada",
                id=item["id"],
                category=item["category"],
                decision=final_result["decision"],
                iterations=final_result["iterations"],
                score=final_result["score"],
            )
    finally:
        await aclose_agents()

    total = len(corpus)
    syntactically_valid = sum(1 for p in per_question if p["syntax_valid"])
    accepted_count = sum(1 for p in per_question if p["decision"] == Decision.ACCEPT.value)

    results = {
        "backend": _backend_label(),
        "total": total,
        "syntactically_valid": syntactically_valid,
        "pct_syntax_valid": round(syntactically_valid / total, 4) if total else 0.0,
        "avg_score": round(sum(p["score"] for p in per_question) / total, 4) if total else 0.0,
        "avg_iterations": round(sum(p["iterations"] for p in per_question) / total, 4) if total else 0.0,
        "pct_accepted": round(accepted_count / total, 4) if total else 0.0,
        "errors_by_type": dict(errors_by_type),
        "by_category": dict(by_category),
        "per_question": per_question,
    }

    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")

    log.info(
        "sistema_completo",
        backend=results["backend"],
        total=total,
        pct_accepted=results["pct_accepted"],
        avg_score=results["avg_score"],
        avg_iterations=results["avg_iterations"],
    )


if __name__ == "__main__":
    asyncio.run(main())
