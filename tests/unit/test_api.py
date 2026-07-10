from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from api.main import app
from models import Decision

client = TestClient(app)


def test_health_returns_ok() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_schema_returns_five_tables() -> None:
    response = client.get("/schema")

    assert response.status_code == 200
    body = response.json()
    assert len(body["tables"]) == 5
    assert {t["name"] for t in body["tables"]} == {
        "Ventas", "Productos", "Clientes", "Calendario", "Tiendas",
    }


def test_query_returns_final_result_shape(mocker) -> None:
    fake_graph = MagicMock()
    fake_graph.ainvoke = AsyncMock(return_value={
        "final_result": {
            "dax": 'EVALUATE ROW("x", 1)',
            "score": 0.95,
            "decision": Decision.ACCEPT,
            "iterations": 1,
            "explanation": "responde correctamente",
            "syntax_valid": True,
        }
    })
    mocker.patch("api.routes.build_graph", return_value=fake_graph)

    response = client.post("/query", json={"question": "¿Cuál es el total de ventas?"})

    assert response.status_code == 200
    body = response.json()
    assert body == {
        "dax": 'EVALUATE ROW("x", 1)',
        "score": 0.95,
        "decision": "ACCEPT",
        "iterations": 1,
        "explanation": "responde correctamente",
        "syntax_valid": True,
    }
    fake_graph.ainvoke.assert_awaited_once()
    called_state = fake_graph.ainvoke.await_args.args[0]
    assert called_state["question"] == "¿Cuál es el total de ventas?"
    assert called_state["iteration"] == 0


def test_query_rejects_missing_question() -> None:
    response = client.post("/query", json={})

    assert response.status_code == 422
