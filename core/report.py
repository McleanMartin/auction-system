from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

def generate_invoice_pdf(payment):
    """Generate a PDF invoice for a payment."""
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="invoice_{payment.transcation_id}.pdf"'

    doc = SimpleDocTemplate(response, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []

    # Add title
    title = Paragraph("Invoice", styles['Title'])
    elements.append(title)
    elements.append(Spacer(1, 12))

    # Add payment details
    details = [
        ["Transaction ID", payment.transcation_id],
        ["Auction", payment.auction],
        ["Item", payment.item],
        ["Amount", f"${payment.amount}"],
        ["Platform Fee", f"${payment.platform_fee}"],
        ["Tax Fee", f"${payment.tax_fee}"],
        ["Total Amount", f"${payment.total_amount}"],
        ["Payment Method", payment.payment_method],
        ["Status", payment.status],
        ["Date", payment.created.strftime("%Y-%m-%d %H:%M:%S")],
    ]

    # Create a table for payment details
    table = Table(details, colWidths=[150, 300])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))

    elements.append(table)
    elements.append(Spacer(1, 24))

    # Add a thank you message
    thank_you = Paragraph("Thank you for your payment!", styles['BodyText'])
    elements.append(thank_you)

    # Build the PDF
    doc.build(elements)
    return response