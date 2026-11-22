
from io import BytesIO
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    KeepTogether,
)

from orders.models import Order


@login_required(login_url="login")
def download_invoice(request, order_uuid):

    # Customers can only download their own invoices.
    order = get_object_or_404(
        Order.objects.prefetch_related("items"),
        order_id=order_uuid,
        user=request.user,
    )

    # Generate the date at the moment of download.
    download_date = timezone.localtime(timezone.now())

    buffer = BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=(595.28, 841.89),
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40,
        title=f"HerSteps Invoice {order.order_id}",
    )

    styles = getSampleStyleSheet()

    styles.add(
        ParagraphStyle(
            name="InvoiceBrand",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=24,
            leading=30,
            textColor=colors.HexColor("#99420A"),
            spaceAfter=6,
        )
    )

    styles.add(
        ParagraphStyle(
            name="InvoiceSmall",
            parent=styles["Normal"],
            fontSize=9,
            leading=15,
            textColor=colors.HexColor("#555555"),
        )
    )

    styles.add(
        ParagraphStyle(
            name="InvoiceRight",
            parent=styles["Normal"],
            fontSize=10,
            leading=16,
            alignment=TA_RIGHT,
        )
    )

    styles.add(
        ParagraphStyle(
            name="InvoiceCenter",
            parent=styles["Normal"],
            fontSize=9,
            leading=14,
            alignment=TA_CENTER,
        )
    )

    story = []

    story.append(
        Paragraph("HERSTEPS", styles["InvoiceBrand"])
    )

    story.append(
        Paragraph(
            "Women's Footwear Store",
            styles["InvoiceSmall"],
        )
    )

    story.append(Spacer(1, 22))

    story.append(
        Paragraph("INVOICE", styles["Heading2"])
    )

    story.append(Spacer(1, 10))

    invoice_number = f"INV-{order.pk:06d}"

    invoice_info = [
        ["Invoice Number", invoice_number],
        ["Order ID", str(order.order_id)],
        [
            "Invoice Date",
            download_date.strftime("%d %B %Y"),
        ],
        [
            "Downloaded At",
            download_date.strftime("%I:%M %p"),
        ],
        [
            "Order Status",
            order.get_order_status_display(),
        ],
        [
            "Payment Method",
            order.get_payment_method_display(),
        ],
        [
            "Payment Status",
            order.get_payment_status_display(),
        ],
    ]

    info_table = Table(
        invoice_info,
        colWidths=[120, 395],
        hAlign="LEFT",
    )

    info_table.setStyle(
        TableStyle([
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#333333")),
        ])
    )

    story.append(info_table)
    story.append(Spacer(1, 22))

    story.append(
        Paragraph("BILL TO / DELIVERY ADDRESS", styles["Heading3"])
    )

    address_lines = [
        order.full_name,
        order.house_name,
        order.locality,
        f"{order.city}, {order.state} - {order.pincode}",
        f"Phone: {order.phone}",
    ]

    for line in address_lines:
        story.append(
            Paragraph(
                str(line or ""),
                styles["InvoiceSmall"],
            )
        )

    story.append(Spacer(1, 24))

    story.append(
        Paragraph("ORDERED PRODUCTS", styles["Heading3"])
    )

    story.append(Spacer(1, 10))

    def money(value):
        return f"INR {Decimal(value):,.2f}"

    product_rows = [[
        "Product / Size",
        "Qty",
        "Unit Price",
        "Amount",
    ]]

    
    for item in order.items.exclude(status="cancelled"):

        product_name = item.product_name

        if item.status == "returned":
            product_name += " (Returned)"

        elif item.status == "return_requested":
            product_name += " (Return Requested)"

        product_rows.append([
            Paragraph(
                f"{product_name}<br/>UK {item.size}",
                styles["InvoiceSmall"],
            ),
            str(item.quantity),
            money(item.price),
            money(item.item_total),
        ])

    product_table = Table(
        product_rows,
        colWidths=[245, 45, 105, 120],
        repeatRows=1,
        hAlign="LEFT",
    )

    product_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F5E5D9")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#5A3320")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
            ("TOPPADDING", (0, 0), (-1, -1), 11),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 11),
            ("LINEBELOW", (0, 0), (-1, 0), 1, colors.HexColor("#D9B9A5")),
            ("LINEBELOW", (0, 1), (-1, -1), 0.4, colors.HexColor("#EAEAEA")),
        ])
    )

    story.append(product_table)
    story.append(Spacer(1, 25))

    # Totals are taken from the order's current saved values.
    # These are recalculated by your cancellation service.
    totals = [
        ["Subtotal", money(order.subtotal)],
        ["Discount", f"- {money(order.discount)}"],
        ["Shipping", money(order.shipping_charge)],
        ["TOTAL AMOUNT", money(order.total_amount)],
    ]

    totals_table = Table(
        totals,
        colWidths=[330, 185],
        hAlign="RIGHT",
    )

    totals_table.setStyle(
        TableStyle([
            ("ALIGN", (1, 0), (1, -1), "RIGHT"),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#F5E5D9")),
            ("TOPPADDING", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
        ])
    )

    story.append(totals_table)
    story.append(Spacer(1, 35))

    story.append(
        Paragraph(
            "Thank you for shopping with HerSteps!",
            styles["InvoiceCenter"],
        )
    )

    story.append(
        Paragraph(
            "This invoice was generated electronically.",
            styles["InvoiceCenter"],
        )
    )

    document.build(story)

    buffer.seek(0)

    filename = f"HerSteps_Invoice_{order.order_id}.pdf"

    return FileResponse(
        buffer,
        as_attachment=True,
        filename=filename,
        content_type="application/pdf",
    )
