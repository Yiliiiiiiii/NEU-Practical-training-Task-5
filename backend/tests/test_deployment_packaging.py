from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read_text(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def parse_env_file(relative_path: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in read_text(relative_path).splitlines():
        if not line or line.startswith("#"):
            continue
        key, value = line.split("=", 1)
        values[key] = value
    return values


def test_deployment_files_are_present():
    expected_files = [
        ".dockerignore",
        ".env.production.example",
        "Dockerfile.backend",
        "Dockerfile.frontend",
        "backend/Dockerfile",
        "frontend/Dockerfile",
        "frontend/nginx.conf",
        "docker-compose.yml",
        "docs/deployment.md",
        "docs/交接/final_demo_script.md",
        "docs/交接/requirement_mapping.md",
        "docs/交接/badcase_analysis.md",
        "docs/api_usage_examples.md",
    ]

    for relative_path in expected_files:
        assert (ROOT / relative_path).is_file(), relative_path


def test_backend_container_initializes_runtime_database():
    dockerfile = read_text("backend/Dockerfile")

    assert "python:3.13-slim" in dockerfile
    assert "STORAGE_ROOT=/data/storage" in dockerfile
    assert "DATABASE_URL=sqlite:////data/db/schemapack.db" in dockerfile
    assert "LLM_FALLBACK_ENABLED=false" in dockerfile
    assert "from app.database import init_db; init_db()" in dockerfile
    assert "uvicorn app.main:app --host 0.0.0.0 --port 8000" in dockerfile


def test_frontend_container_proxies_api_to_backend():
    dockerfile = read_text("frontend/Dockerfile")
    nginx_conf = read_text("frontend/nginx.conf")

    assert "npm run build" in dockerfile
    assert "nginx:1.27-alpine" in dockerfile
    assert "location /api/" in nginx_conf
    assert "proxy_pass http://backend:8000" in nginx_conf
    assert "try_files $uri $uri/ /index.html" in nginx_conf


def test_compose_profile_uses_persistent_runtime_volumes():
    compose = read_text("docker-compose.yml")

    assert "dockerfile: backend/Dockerfile" in compose
    assert "dockerfile: frontend/Dockerfile" in compose
    assert "sqlite:////data/db/schemapack.db" in compose
    assert "schemapack_storage:/data/storage" in compose
    assert "schemapack_db:/data/db" in compose
    assert "8080:80" in compose


def test_production_env_example_is_safe_by_default():
    values = parse_env_file(".env.production.example")

    assert values["APP_ENV"] == "production"
    assert values["STORAGE_ROOT"] == "/data/storage"
    assert values["DATABASE_URL"] == "sqlite:////data/db/schemapack.db"
    assert values["LLM_MODE"] == "disabled"
    assert values["LLM_FALLBACK_ENABLED"] == "false"
    assert values["OFFLINE_MODE"] == "true"
