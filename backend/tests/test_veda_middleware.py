"""Unit tests for VedaElectoralMiddleware.

S3.5: verifies that internal plan operations remain operational during veda
while external publication paths stay blocked.
"""

from __future__ import annotations

import pytest
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from app.core.veda import VedaElectoralMiddleware


@pytest.fixture(autouse=True)
def _activate_veda(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force veda active for the duration of each test without side effects."""
    from app.core import veda as veda_module

    monkeypatch.setattr(veda_module, "_is_veda_active", lambda: True)


def _build_app() -> TestClient:
    async def ok(_request):
        return JSONResponse({"status": "ok"})

    routes = [
        Route("/api/v1/auth/login", ok, methods=["POST"]),
        Route("/api/v1/health/", ok, methods=["GET"]),
        Route("/api/v1/planes/generar", ok, methods=["POST"]),
        Route("/api/v1/planes/1", ok, methods=["GET"]),
        Route("/api/v1/planes/1/tareas", ok, methods=["GET"]),
        Route("/api/v1/planes/1/tareas/7", ok, methods=["PATCH"]),
        Route("/api/v1/planes/1/tareas/7/complete", ok, methods=["POST"]),
        Route("/api/v1/social/posts", ok, methods=["POST"]),
        Route("/api/v1/encuestas", ok, methods=["POST"]),
        Route("/api/v1/content/pieces/5", ok, methods=["PATCH"]),
        Route("/api/v1/content/generate", ok, methods=["POST"]),
        Route("/api/v1/dashboard/overview", ok, methods=["GET"]),
    ]
    app = Starlette(routes=routes, middleware=[])
    app.add_middleware(VedaElectoralMiddleware)
    return TestClient(app)


class TestVedaAllowsInternalPlanOperations:
    """S3.5: planes IA son análisis interno → deben pasar durante veda."""

    def test_generar_plan_pass(self) -> None:
        client = _build_app()
        resp = client.post("/api/v1/planes/generar")
        assert resp.status_code == 200

    def test_list_tareas_pass(self) -> None:
        client = _build_app()
        resp = client.get("/api/v1/planes/1/tareas")
        assert resp.status_code == 200

    def test_patch_tarea_pass(self) -> None:
        client = _build_app()
        resp = client.patch("/api/v1/planes/1/tareas/7")
        assert resp.status_code == 200

    def test_complete_tarea_pass(self) -> None:
        client = _build_app()
        resp = client.post("/api/v1/planes/1/tareas/7/complete")
        assert resp.status_code == 200


class TestVedaBlocksExternalPublication:
    """Publicaciones externas y encuestas siguen bloqueadas."""

    def test_social_post_blocked(self) -> None:
        client = _build_app()
        resp = client.post("/api/v1/social/posts")
        assert resp.status_code == 403
        assert "veda electoral" in resp.json()["detail"].lower()

    def test_encuesta_post_blocked(self) -> None:
        client = _build_app()
        resp = client.post("/api/v1/encuestas")
        assert resp.status_code == 403

    def test_content_approve_blocked(self) -> None:
        client = _build_app()
        resp = client.patch("/api/v1/content/pieces/5")
        assert resp.status_code == 403

    def test_content_generate_blocked(self) -> None:
        client = _build_app()
        resp = client.post("/api/v1/content/generate")
        assert resp.status_code == 403


class TestVedaPassthrough:
    """Auth, health y todas las GET siguen operativos."""

    def test_auth_pass(self) -> None:
        client = _build_app()
        resp = client.post("/api/v1/auth/login")
        assert resp.status_code == 200

    def test_health_pass(self) -> None:
        client = _build_app()
        resp = client.get("/api/v1/health/")
        assert resp.status_code == 200

    def test_get_pass(self) -> None:
        client = _build_app()
        resp = client.get("/api/v1/dashboard/overview")
        assert resp.status_code == 200

    def test_get_plan_pass(self) -> None:
        client = _build_app()
        resp = client.get("/api/v1/planes/1")
        assert resp.status_code == 200
