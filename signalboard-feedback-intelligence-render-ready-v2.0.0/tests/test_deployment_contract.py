from feedback_intelligence_engine import __version__


def test_health_uses_package_version(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["version"] == __version__


def test_runtime_reads_render_port(monkeypatch):
    import feedback_intelligence_engine.main as module

    captured = {}

    def fake_run(*args, **kwargs):
        captured.update({"args": args, "kwargs": kwargs})

    monkeypatch.setenv("PORT", "10000")
    monkeypatch.setattr(module.uvicorn, "run", fake_run)
    module.run()

    assert captured["kwargs"]["host"] == "0.0.0.0"
    assert captured["kwargs"]["port"] == 10000
    assert captured["kwargs"]["proxy_headers"] is True


def test_render_blueprint_is_single_service_with_postgres():
    from pathlib import Path

    blueprint = (Path(__file__).resolve().parents[1] / "render.yaml").read_text()
    assert "runtime: docker" in blueprint
    assert "healthCheckPath: /api/v1/health" in blueprint
    assert "fromDatabase:" in blueprint
    assert "plan: free" in blueprint
    assert "GITHUB_TOKEN" in blueprint


def test_database_url_normalization_for_render_postgres():
    from feedback_intelligence_engine.db import normalize_database_url

    assert (
        normalize_database_url("postgres://user:pass@host/db")
        == "postgresql+psycopg://user:pass@host/db"
    )
    assert (
        normalize_database_url("postgresql://user:pass@host/db")
        == "postgresql+psycopg://user:pass@host/db"
    )
    assert normalize_database_url("sqlite:///local.db") == "sqlite:///local.db"
