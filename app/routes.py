import re
import threading
import uuid

from flask import Blueprint, abort, current_app, jsonify, request, send_file

from app import db
from app.models import Certificate, Job
from app.worker import process_job

api = Blueprint("api", __name__)
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def validate_request(data):
    if not isinstance(data, dict):
        return "Request body must be a JSON object"
    recipients = data.get("recipients")
    if not isinstance(recipients, list) or not recipients:
        return "recipients must be a non-empty list"
    if len(recipients) > current_app.config["MAX_RECIPIENTS"]:
        return f"recipients cannot exceed {current_app.config['MAX_RECIPIENTS']}"
    for index, recipient in enumerate(recipients):
        if not isinstance(recipient, dict):
            return f"recipients[{index}] must be an object"
        name, email, course = (recipient.get(key) for key in ("name", "email", "course_name"))
        if not isinstance(name, str) or not name.strip() or len(name.strip()) > 200:
            return f"recipients[{index}].name must be 1-200 characters"
        if not isinstance(email, str) or len(email) > 254 or not EMAIL_RE.match(email):
            return f"recipients[{index}].email must be a valid email address"
        if not isinstance(course, str) or not course.strip() or len(course.strip()) > 200:
            return f"recipients[{index}].course_name must be 1-200 characters"
    return None


def certificate_json(item):
    return {
        "id": item.id,
        "recipient_name": item.recipient_name,
        "recipient_email": item.recipient_email,
        "course_name": item.course_name,
        "status": item.status,
        "error": item.error_message,
        "download_url": f"/api/certificates/{item.id}" if item.status == "succeeded" else None,
    }


@api.post("/jobs")
def create_job():
    data = request.get_json(silent=True)
    error = validate_request(data)
    if error:
        return jsonify({"error": error}), 400

    job = Job(id=str(uuid.uuid4()), total_count=len(data["recipients"]))
    db.session.add(job)
    for recipient in data["recipients"]:
        db.session.add(Certificate(
            id=str(uuid.uuid4()), job_id=job.id,
            recipient_name=recipient["name"].strip(),
            recipient_email=recipient["email"].strip(),
            course_name=recipient["course_name"].strip(),
        ))
    db.session.commit()

    app = current_app._get_current_object()
    threading.Thread(target=process_job, args=(app, job.id), daemon=True).start()
    return jsonify({"job_id": job.id, "status": job.status, "total_count": job.total_count,
                    "status_url": f"/api/jobs/{job.id}"}), 202


@api.get("/jobs/<job_id>")
def get_job(job_id):
    job = db.session.get(Job, job_id)
    if job is None:
        abort(404)
    return jsonify({"id": job.id, "status": job.status, "total_count": job.total_count,
                    "success_count": job.success_count, "failure_count": job.failure_count,
                    "completed_count": job.success_count + job.failure_count,
                    "created_at": job.created_at.isoformat(),
                    "completed_at": job.completed_at.isoformat() if job.completed_at else None})


@api.get("/jobs/<job_id>/certificates")
def list_certificates(job_id):
    if db.session.get(Job, job_id) is None:
        abort(404)
    items = Certificate.query.filter_by(job_id=job_id).order_by(Certificate.created_at).all()
    return jsonify({"certificates": [certificate_json(item) for item in items]})


@api.get("/certificates/<certificate_id>")
def get_certificate(certificate_id):
    item = db.session.get(Certificate, certificate_id)
    if item is None:
        abort(404)
    if item.status != "succeeded" or not item.file_path:
        return jsonify({"error": "certificate is not available", "status": item.status}), 409
    return send_file(item.file_path, mimetype="application/pdf", as_attachment=True,
                     download_name=f"certificate-{item.id}.pdf")
