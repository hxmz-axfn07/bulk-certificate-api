from unittest.mock import patch

def payload(*recipients):
    return {"recipients": [
        {"name": name, "email": f"{name.lower()}@example.com", "course_name": "Python 101"}
        for name in recipients
    ]}


def test_create_job_and_track_progress(client, wait_for_job):
    response = client.post("/api/jobs", json=payload("Ada", "Grace"))
    assert response.status_code == 202
    job_id = response.json["job_id"]
    result = wait_for_job(job_id)
    assert result["total_count"] == 2
    assert result["success_count"] == 2
    assert result["failure_count"] == 0


def test_invalid_input(client):
    for body in ({}, {"recipients": []}, payload("Ada") | {"recipients": [{"name": "Ada"}]},
                 {"recipients": [None]}):
        assert client.post("/api/jobs", json=body).status_code == 400


def test_generation_creates_pdf(client, wait_for_job):
    response = client.post("/api/jobs", json=payload("Ada"))
    wait_for_job(response.json["job_id"])
    result = client.get(f"/api/jobs/{response.json['job_id']}/certificates").json
    assert result["certificates"][0]["status"] == "succeeded"
    from pathlib import Path
    pdf_path = Path(client.application.config["CERTIFICATE_DIR"]) / f"{result['certificates'][0]['id']}.pdf"
    assert pdf_path.read_bytes().startswith(b"%PDF")


def test_one_generation_failure_does_not_stop_batch(client, wait_for_job):
    from app import worker
    real_generate = worker.generate_certificate

    def fail_first(name, course, path):
        if name == "Ada":
            raise RuntimeError("printer error")
        real_generate(name, course, path)

    with patch.object(worker, "generate_certificate", side_effect=fail_first):
        response = client.post("/api/jobs", json=payload("Ada", "Grace"))
        job = wait_for_job(response.json["job_id"])
    assert (job["success_count"], job["failure_count"]) == (1, 1)
    certificates = client.get(f"/api/jobs/{response.json['job_id']}/certificates").json["certificates"]
    assert [item["status"] for item in certificates].count("failed") == 1


def test_retrieve_generated_certificate(client, wait_for_job):
    response = client.post("/api/jobs", json=payload("Ada"))
    wait_for_job(response.json["job_id"])
    certificate = client.get(f"/api/jobs/{response.json['job_id']}/certificates").json["certificates"][0]
    download = client.get(certificate["download_url"])
    assert download.status_code == 200
    assert download.mimetype == "application/pdf"
    assert download.data.startswith(b"%PDF")


def test_startup_creates_missing_mysql_database():
    from unittest.mock import MagicMock
    from app import ensure_mysql_database

    server_engine = MagicMock()
    server_engine.dialect.identifier_preparer.quote_identifier.return_value = "`certificates`"
    connection = server_engine.begin.return_value.__enter__.return_value
    with patch("app.create_engine", return_value=server_engine) as create_engine:
        ensure_mysql_database("mysql+pymysql://user:password@localhost/certificates")

    create_engine.assert_called_once()
    assert create_engine.call_args.args[0].database is None
    connection.exec_driver_sql.assert_called_once_with(
        "CREATE DATABASE IF NOT EXISTS `certificates`"
    )
    server_engine.dispose.assert_called_once()
