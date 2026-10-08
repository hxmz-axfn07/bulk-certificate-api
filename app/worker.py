import os
from datetime import datetime, timezone

from app import db
from app.certificate import generate_certificate
from app.models import Certificate, Job


def process_job(app, job_id):
    """Process recipients independently, recording each outcome in the DB."""
    with app.app_context():
        job = db.session.get(Job, job_id)
        if job is None:
            return
        job.status = "processing"
        db.session.commit()

        certificate_ids = [item.id for item in job.certificates]
        for certificate_id in certificate_ids:
            item = db.session.get(Certificate, certificate_id)
            try:
                output_path = os.path.join(app.config["CERTIFICATE_DIR"], f"{item.id}.pdf")
                generate_certificate(item.recipient_name, item.course_name, output_path)
                item.file_path = output_path
                item.status = "succeeded"
                job.success_count += 1
            except Exception as error:  # A bad recipient must not stop the batch.
                item.status = "failed"
                item.error_message = str(error)[:500] or "Certificate generation failed"
                job.failure_count += 1
            finally:
                item.completed_at = datetime.now(timezone.utc)
                db.session.commit()

        job.status = "completed"
        job.completed_at = datetime.now(timezone.utc)
        db.session.commit()
