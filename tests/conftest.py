import pytest

from app import create_app, db


@pytest.fixture
def app(tmp_path):
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'test.db'}",
        "CERTIFICATE_DIR": str(tmp_path / "generated"),
    })
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def wait_for_job(client):
    def wait(job_id):
        import time
        for _ in range(200):
            response = client.get(f"/api/jobs/{job_id}")
            if response.json["status"] == "completed":
                return response.json
            time.sleep(0.01)
        raise AssertionError("job did not finish")
    return wait
