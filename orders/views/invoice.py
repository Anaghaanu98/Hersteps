
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
from xml.sax.saxutils import escape

from reportlab.graphics.shapes import Drawing, Path, String
from reportlab.lib.colors import HexColor
from django.http import Http404



@login_required(login_url="login")
def download_invoice(request, order_uuid):

    # Customers can only download their own invoices.
    order = get_object_or_404(
        Order.objects.prefetch_related("items"),
        order_id=order_uuid,
        user=request.user,
    )
    if order.order_status != "delivered":
     raise Http404("Invoice is available only after delivery.")

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

    # HerSteps logo - matching base.html
    logo = Drawing(240, 45)

    droplet = Path(
        fillColor=HexColor("#C9652A"),
        strokeColor=None,
    )

    droplet.moveTo(11, 45)
    droplet.curveTo(4, 39, 0, 33, 0, 26.5)
    droplet.curveTo(0, 20, 4.6, 15, 11, 15)
    droplet.curveTo(17.4, 15, 22, 20, 22, 26.5)
    droplet.curveTo(22, 33, 18, 39, 11, 45)
    droplet.closePath()

    logo.add(droplet)

    logo.add(String(
        33, 23,
        "hersteps",
        fontName="Times-Bold",
        fontSize=27,
        fillColor=HexColor("#231915"),
    ))

    logo.add(String(
        34, 11,
        "FOOTWEAR FOR WOMEN",
        fontName="Helvetica-Bold",
        fontSize=6.5,
        fillColor=HexColor("#897D75"),
    ))

    logo.hAlign = "LEFT"

    story.append(logo)
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



@login_required(login_url="login")
def download_purchase_order(request, order_id):

    order = get_object_or_404(
        Order.objects.prefetch_related("items"),
        order_id=order_id,
        user=request.user
    )

    buffer = BytesIO()

    pdf = SimpleDocTemplate(
        buffer,
        pagesize=(595, 842),
        rightMargin=40,
        leftMargin=40,
        topMargin=45,
        bottomMargin=45,
        title=f"HerSteps Purchase Order {order.order_id}",
    )

    elements = []
    styles = getSampleStyleSheet()

    brown = HexColor("#99420A")
    orange = HexColor("#C9652A")
    muted = HexColor("#897D75")
    peach = HexColor("#FFF0E5")

    styles.add(ParagraphStyle(
        name="PurchaseHeading",
        parent=styles["Heading2"],
        fontSize=16,
        leading=22,
        textColor=brown,
        spaceAfter=15,
    ))

    styles.add(ParagraphStyle(
        name="PurchaseNormal",
        parent=styles["Normal"],
        fontSize=10,
        leading=17,
        textColor=HexColor("#342922"),
    ))

    styles.add(ParagraphStyle(
        name="PurchaseSmall",
        parent=styles["Normal"],
        fontSize=9,
        leading=15,
        textColor=muted,
    ))

    # HERSTEPS LOGO
    # Recreates the SVG mark and text from base.html

    logo = Drawing(240, 45)

    droplet = Path(
        fillColor=orange,
        strokeColor=None,
    )

    # Same droplet path as the navbar SVG.
    # SVG coordinates are transformed to ReportLab coordinates.
    droplet.moveTo(11, 45)
    droplet.curveTo(4, 39, 0, 33, 0, 26.5)
    droplet.curveTo(0, 20, 4.6, 15, 11, 15)
    droplet.curveTo(17.4, 15, 22, 20, 22, 26.5)
    droplet.curveTo(22, 33, 18, 39, 11, 45)
    droplet.closePath()

    logo.add(droplet)

    logo.add(String(
        33, 23,
        "hersteps",
        fontName="Times-Bold",
        fontSize=27,
        fillColor=HexColor("#231915"),
    ))

    logo.add(String(
        34, 11,
        "FOOTWEAR FOR WOMEN",
        fontName="Helvetica-Bold",
        fontSize=6.5,
        fillColor=muted,
    ))

    logo.hAlign = "LEFT"
    elements.append(logo)

    elements.append(Spacer(1, 15))

    elements.append(
        Paragraph(
            "PURCHASE ORDER",
            styles["PurchaseHeading"]
        )
    )

    # ORDER ID AND DOWNLOAD DATE
    download_date = timezone.localdate()

    details = [
        [
            "Order ID",
            Paragraph(
                escape(str(order.order_id)),
                styles["PurchaseNormal"]
            )
        ],
        [
            "Download Date",
            download_date.strftime("%d %B %Y")
        ],
    ]

    details_table = Table(
        details,
        colWidths=[130, 385],
        hAlign="LEFT",
    )

    details_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))

    elements.append(details_table)
    elements.append(Spacer(1, 18))

    # DELIVERY ADDRESS
    elements.append(
        Paragraph(
            "Delivery Address",
            styles["PurchaseHeading"]
        )
    )

    address_lines = [
        order.full_name,
        order.house_name,
        order.locality,
        f"{order.city}, {order.state} - {order.pincode}",
        f"Phone: {order.phone}",
    ]

    for line in address_lines:
        elements.append(
            Paragraph(
                escape(str(line or "")),
                styles["PurchaseNormal"]
            )
        )

    elements.append(Spacer(1, 22))

    # ORDER DETAILS
    elements.append(
        Paragraph(
            "Order Details",
            styles["PurchaseHeading"]
        )
    )

    def money(value):
        return f"Rs. {Decimal(value):,.2f}"

    product_rows = [[
        "Product",
        "Size",
        "Qty",
        "Amount",
    ]]

    # Include all original items, even if later cancelled
    # or returned, so the purchase record remains complete.
    for item in order.items.all():

        product_rows.append([
            Paragraph(
                escape(str(item.product_name)),
                styles["PurchaseNormal"]
            ),
            f"UK {item.size}",
            str(item.quantity),
            money(item.item_total),
        ])

    product_table = Table(
        product_rows,
        colWidths=[245, 65, 55, 150],
        repeatRows=1,
        hAlign="LEFT",
    )

    product_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), peach),
        ("TEXTCOLOR", (0, 0), (-1, 0), brown),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
        ("TOPPADDING", (0, 0), (-1, -1), 11),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 11),
        (
            "LINEBELOW",
            (0, 0),
            (-1, -1),
            0.5,
            HexColor("#EAEAEA")
        ),
    ]))

    elements.append(product_table)
    elements.append(Spacer(1, 25))

    # TOTAL AMOUNT
    total_data = [[
        "TOTAL ORDER AMOUNT",
        money(order.total_amount)
    ]]

    total_table = Table(
        total_data,
        colWidths=[330, 185],
        hAlign="LEFT",
    )

    total_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), peach),
        ("TEXTCOLOR", (0, 0), (-1, -1), brown),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 12),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("TOPPADDING", (0, 0), (-1, -1), 15),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 15),
    ]))

    elements.append(total_table)

    pdf.build(elements)

    buffer.seek(0)

    return FileResponse(
        buffer,
        as_attachment=True,
        filename=f"HerSteps_Purchase_Order_{order.order_id}.pdf",
        content_type="application/pdf",
    )
