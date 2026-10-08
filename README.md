# Bulk Certificate Generator

A Flask API that accepts a batch of recipients, generates a PDF certificate for each one, and reports job and individual certificate results. It uses MySQL for job data and ReportLab for a single fixed certificate design.

## Requirements

- Python 3.10 or newer
- MySQL 8 or newer

## Setup

Create and activate a virtual environment, then install the dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Create a MySQL account for the app. Startup creates the configured database, so the account needs the global `CREATE` privilege and access to the application database:

```sql
CREATE USER 'certificates'@'localhost' IDENTIFIED BY 'choose-a-password';
GRANT CREATE ON *.* TO 'certificates'@'localhost';
GRANT ALL PRIVILEGES ON certificates.* TO 'certificates'@'localhost';
```

Copy `.env.example` to `.env` and update the database username and password:

```bash
cp .env.example .env
```

Example configuration:

```env
DATABASE_URL=mysql+pymysql://certificates:choose-a-password@127.0.0.1:3306/certificates
CERTIFICATE_DIR=generated
```

The app loads `.env` on startup. Variables already set in the shell take precedence. If a password contains URL-reserved characters such as `@`, `:`, `/`, or `#`, URL-encode those characters in `DATABASE_URL`. Do not commit `.env`; it is ignored by Git.

## Run the server

Make sure MySQL is running, then start Flask:

```bash
python run.py
```

The development server listens at `http://127.0.0.1:5000`. Startup creates the configured MySQL database if needed and creates missing tables. The database account must have the privileges described above.

## API usage

Submit one or more recipients in a single request. Each needs a name, email, and course name. The maximum batch size is 500.

```bash
curl -X POST http://127.0.0.1:5000/api/jobs \
  -H 'Content-Type: application/json' \
  -d '{"recipients":[{"name":"Ada Lovelace","email":"ada@example.com","course_name":"Python 101"},{"name":"Grace Hopper","email":"grace@example.com","course_name":"Python 101"}]}'
```

The API returns `202 Accepted` with a `job_id`, for example:

```json
{"job_id":"JOB_UUID","status":"queued","total_count":2,"status_url":"/api/jobs/JOB_UUID"}
```

Check progress using the returned job ID:

```bash
curl http://127.0.0.1:5000/api/jobs/JOB_UUID
```

List each recipient’s result and retrieve the successful certificate’s ID:

```bash
curl http://127.0.0.1:5000/api/jobs/JOB_UUID/certificates
```

Download an individual generated PDF using its certificate ID:

```bash
curl -OJ http://127.0.0.1:5000/api/certificates/CERTIFICATE_UUID
```

The job status response includes total, completed, successful, and failed counts. The certificate list includes an individual status, any error, and a download URL for successful certificates. Invalid request data returns `400`; unknown IDs return `404`; certificates that are queued or failed return `409` when downloaded.

## Run tests

Tests use temporary SQLite storage and a temporary PDF directory; they do not need a MySQL server:

```bash
python -m pytest -q
```

The suite covers job creation and progress, invalid input, PDF generation, individual generation failures, PDF retrieval, and MySQL database creation at startup.

## Design decisions

- **Bulk API:** One request creates one job and a database record for each recipient, rather than requiring one HTTP request per certificate.
- **Independent results:** The worker catches generation errors per recipient and commits each result, allowing the rest of the batch to continue.
- **Background thread:** A daemon thread keeps the request short without adding a broker. This is suitable for a small, single-process assignment. Work is lost if the process exits, and multiple app processes do not coordinate jobs; durable production processing would need a persistent queue.
- **PDF storage:** ReportLab writes files under `CERTIFICATE_DIR`; MySQL stores their paths and status. Keep the output directory persistent if certificates must remain downloadable.
- **Schema changes:** `db.create_all()` creates missing tables but does not migrate existing table schemas. A deployed service would use database migrations when the schema evolves.
- **Validation:** The API enforces required fields, field lengths, basic email syntax, and a batch-size limit. The email check does not verify that an address exists.
