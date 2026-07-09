from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from pathlib import Path

from agents.generator_agent import GeneratorAgent
from config.logging_config import configure_logging, get_logger
from config.settings import settings

CORPUS_PATH = Path("tests/fixtures/corpus.json")
RESULTS_PATH = Path("results/baseline.json")

log = get_logger(__name__)


def _backend_label() -> str:
    if settings.gemini_api_key:
        return f"gemini:{settings.generator_model}"
    return f"local:{settings.local_model}"


async def main() -> None:
    configure_logging()
    corpus = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))

    agent = GeneratorAgent(model=settings.generator_model, temperature=settings.generator_temperature)
    per_question = []
    by_category: dict[str, dict[str, int]] = defaultdict(lambda: {"total": 0, "valid": 0})

    try:
        for item in corpus:
            dax_query = await agent.run(item["question"])
            validation = await agent.call_tool("validate_syntax", dax_query=dax_query.query_text)
            valid = bool(validation["valid"])

            by_category[item["category"]]["total"] += 1
            if valid:
                by_category[item["category"]]["valid"] += 1

            per_question.append({
                "id": item["id"],
                "dax": dax_query.query_text,
                "valid": valid,
                "error": validation["error"],
            })
            log.info("pregunta_procesada", id=item["id"], category=item["category"], valid=valid)
    finally:
        await agent.close()

    total = len(corpus)
    syntactically_valid = sum(1 for p in per_question if p["valid"])

    results = {
        "backend": _backend_label(),
        "total": total,
        "syntactically_valid": syntactically_valid,
        "pct_syntax_valid": round(syntactically_valid / total, 4) if total else 0.0,
        "by_category": dict(by_category),
        "per_question": per_question,
    }

    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")

    log.info(
        "baseline_completo",
        backend=results["backend"],
        total=total,
        pct_syntax_valid=results["pct_syntax_valid"],
    )


if __name__ == "__main__":
    asyncio.run(main())
