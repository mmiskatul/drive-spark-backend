from fastapi.testclient import TestClient

from app.main import create_app


def test_app_factory_creates_app() -> None:
    app = create_app()
    client = TestClient(app)
    assert client.app.title
