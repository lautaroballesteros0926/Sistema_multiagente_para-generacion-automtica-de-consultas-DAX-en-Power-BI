from __future__ import annotations

from langgraph.graph import END, StateGraph

from agents.evaluator_agent import EvaluatorAgent
from agents.generator_agent import GeneratorAgent
from config.logging_config import get_logger
from config.settings import settings
from models import Decision
from orchestrator.state import AgentState

log = get_logger(__name__)

_generator = GeneratorAgent(model=settings.generator_model, temperature=settings.generator_temperature)
_evaluator = EvaluatorAgent(model=settings.evaluator_model, temperature=settings.evaluator_temperature)


async def generate_node(state: AgentState) -> dict:
    feedback = state["evaluation"].feedback_for_generator if state["evaluation"] else None
    dax_query = await _generator.run(state["question"], feedback=feedback)
    iteration = state["iteration"] + 1

    log.info("generate_node", iteration=iteration, feedback_used=feedback is not None)
    return {"dax_query": dax_query, "iteration": iteration}


async def evaluate_node(state: AgentState) -> dict:
    evaluation = await _evaluator.run(state["question"], state["dax_query"])

    log.info(
        "evaluate_node",
        iteration=state["iteration"],
        score=evaluation.score,
        decision=evaluation.decision,
    )
    return {"evaluation": evaluation}


def route_decision(state: AgentState) -> str:
    decision = state["evaluation"].decision

    if decision == Decision.REGENERATE and state["iteration"] >= state["max_iterations"]:
        return Decision.REJECT.value

    return decision.value


async def finalize_node(state: AgentState) -> dict:
    decision = Decision(route_decision(state))

    final_result = {
        "dax": state["dax_query"].query_text,
        "score": state["evaluation"].score,
        "decision": decision,
        "iterations": state["iteration"],
        "explanation": state["evaluation"].explanation,
        "syntax_valid": state["evaluation"].syntax_valid,
    }

    log.info("finalize_node", **final_result)
    return {"final_result": final_result}


def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("generate", generate_node)
    graph.add_node("evaluate", evaluate_node)
    graph.add_node("finalize", finalize_node)

    graph.set_entry_point("generate")
    graph.add_edge("generate", "evaluate")
    graph.add_conditional_edges(
        "evaluate",
        route_decision,
        {
            Decision.ACCEPT.value: "finalize",
            Decision.REJECT.value: "finalize",
            Decision.REGENERATE.value: "generate",
        },
    )
    graph.add_edge("finalize", END)

    return graph.compile()


async def aclose_agents() -> None:
    """Cierra las sesiones MCP de los agentes singleton del grafo.

    Quien use `build_graph()` en un script o servidor de larga vida debe
    llamar esto al apagar (lifespan de la API, `finally` de un script) para
    no dejar los subprocesos MCP colgando.
    """
    await _generator.close()
    await _evaluator.close()
