import os

from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas


def generate_certificate(recipient_name, course_name, output_path):
    """Draw the project's single, fixed certificate design as a PDF."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    page = landscape(letter)
    pdf = canvas.Canvas(output_path, pagesize=page)
    width, height = page
    pdf.setStrokeColorRGB(0.12, 0.32, 0.48)
    pdf.setLineWidth(4)
    pdf.rect(0.4 * inch, 0.4 * inch, width - 0.8 * inch, height - 0.8 * inch)
    pdf.setFillColorRGB(0.12, 0.32, 0.48)
    pdf.setFont("Helvetica-Bold", 30)
    pdf.drawCentredString(width / 2, height - 1.8 * inch, "CERTIFICATE OF COMPLETION")
    pdf.setFillColorRGB(0, 0, 0)
    pdf.setFont("Helvetica", 16)
    pdf.drawCentredString(width / 2, height - 2.8 * inch, "This certificate is presented to")
    pdf.setFont("Helvetica-Bold", 27)
    pdf.drawCentredString(width / 2, height - 3.6 * inch, recipient_name)
    pdf.setFont("Helvetica", 16)
    pdf.drawCentredString(width / 2, height - 4.3 * inch, f"for completing {course_name}")
    pdf.showPage()
    pdf.save()
