from datetime import datetime, timezone

from app import db


def now_utc():
    return datetime.now(timezone.utc)


class Job(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    status = db.Column(db.String(20), nullable=False, default="queued")
    total_count = db.Column(db.Integer, nullable=False)
    success_count = db.Column(db.Integer, nullable=False, default=0)
    failure_count = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=now_utc)
    completed_at = db.Column(db.DateTime(timezone=True))
    certificates = db.relationship("Certificate", backref="job", lazy=True)


class Certificate(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    job_id = db.Column(db.String(36), db.ForeignKey("job.id"), nullable=False)
    recipient_name = db.Column(db.String(200), nullable=False)
    recipient_email = db.Column(db.String(254), nullable=False)
    course_name = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="queued")
    file_path = db.Column(db.String(500))
    error_message = db.Column(db.String(500))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=now_utc)
    completed_at = db.Column(db.DateTime(timezone=True))
