import io

from django.http import HttpResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from reports.sales_report import calc_avb, format_money, total_income_from_data


def pdf_response(filename, buffer):
    response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


def _money_cell(value):
    if value in ("", None):
        return "—"
    return f"₹{format_money(value)}"


def _avb_cell(income, walkins):
    avb = calc_avb(income, walkins)
    return _money_cell(avb) if avb is not None else "—"


def build_dsr_display_pdf(filename, display):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    story = [
        Paragraph("Sales Report", styles["Title"]),
        Paragraph(f"Branch: {display['branch_name']}", styles["Normal"]),
        Paragraph(f"Period: {display['period_label']}", styles["Normal"]),
        Spacer(1, 16),
    ]

    income_rows = [
        ["Income", ""],
        ["Net Service income", _money_cell(display["net_service_income"])],
        ["Membership Card", _money_cell(display["membership_card"])],
        ["Ear Piercing", _money_cell(display["ear_piercing"])],
        ["Other Income", _money_cell(display["other_income"])],
        ["Product Sale 18%", _money_cell(display["product_sale_18"])],
        ["Product Sale 5%", _money_cell(display["product_sale_5"])],
        ["GST", _money_cell(display["gst"])],
        ["Bridal Advance", _money_cell(display["bridal_advance"])],
        ["Total Income", _money_cell(display.get("total_income", total_income_from_data(display)))],
    ]
    story.append(_styled_table(income_rows, [260, 180]))
    story.append(Spacer(1, 12))

    walkin_rows = [
        ["Walk Ins", "Count", "Income", "AVB"],
        [
            "Male",
            str(display["male_walkins"]),
            _money_cell(display["male_income"]),
            _avb_cell(display["male_income"], display["male_walkins"]),
        ],
        [
            "Female",
            str(display["female_walkins"]),
            _money_cell(display["female_income"]),
            _avb_cell(display["female_income"], display["female_walkins"]),
        ],
        [
            "Kids",
            str(display["kids_walkins"]),
            _money_cell(display["kids_income"]),
            _avb_cell(display["kids_income"], display["kids_walkins"]),
        ],
        [
            "Total",
            str(display.get("total_walkins", 0)),
            _money_cell(display.get("total_walkin_income", 0)),
            _avb_cell(
                display.get("total_walkin_income", 0),
                display.get("total_walkins", 0),
            ),
        ],
    ]
    story.append(_styled_table(walkin_rows, [120, 70, 110, 90]))
    story.append(Spacer(1, 12))

    payment_rows = [
        ["Mode of Payment", ""],
        ["Card Payment", _money_cell(display["card_payment"])],
        ["UPI", _money_cell(display["upi_payment"])],
        ["Cash Payment", _money_cell(display["cash_payment"])],
        ["Total", _money_cell(display.get("payment_total", 0))],
    ]
    story.append(_styled_table(payment_rows, [260, 180]))
    story.append(Spacer(1, 12))

    marketing_rows = [
        ["Marketing Updates", ""],
        ["No. of calls done", str(display["calls_done"])],
        ["Zooty Appointment", str(display["zooty_appointment"])],
        ["By Google appointment", str(display["google_appointment"])],
        ["Just dial", str(display["just_dial"])],
        ["Broadcast", str(display["broadcast"])],
        ["No of New Clients", str(display["new_clients"])],
    ]
    story.append(_styled_table(marketing_rows, [260, 180]))
    story.append(Spacer(1, 12))

    staff_rows = [["Staff Performance", "Amount"]]
    for line in display["staff_lines"]:
        staff_rows.append([line["staff_name"], _money_cell(line["amount"])])
    staff_rows.append(["Total", _money_cell(display.get("staff_total", 0))])
    story.append(_styled_table(staff_rows, [260, 180]))

    doc.build(story)
    buffer.seek(0)
    return pdf_response(filename, buffer)


def build_yearly_pdf(filename, branch_name, period_label, headers, rows):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=24,
        leftMargin=24,
        topMargin=36,
        bottomMargin=36,
    )
    styles = getSampleStyleSheet()
    story = [
        Paragraph("Yearly Sales Report", styles["Title"]),
        Paragraph(f"Branch: {branch_name}", styles["Normal"]),
        Paragraph(f"Period: {period_label}", styles["Normal"]),
        Spacer(1, 16),
    ]

    table_data = [headers]
    for row in rows:
        formatted = []
        for index, cell in enumerate(row):
            if index == 0:
                formatted.append(str(cell))
            elif cell == "":
                formatted.append("—")
            elif isinstance(cell, float):
                formatted.append(f"{cell:.2f}")
            else:
                formatted.append(str(cell))
        table_data.append(formatted)

    col_count = len(headers)
    page_width = landscape(A4)[0] - 48
    col_width = page_width / col_count
    story.append(_styled_table(table_data, [col_width] * col_count, header=True))
    doc.build(story)
    buffer.seek(0)
    return pdf_response(filename, buffer)


def build_incentive_pdf(filename, period_label, period_type, headers, rows):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=24,
        leftMargin=24,
        topMargin=28,
        bottomMargin=28,
    )
    styles = getSampleStyleSheet()
    type_label = {"daily": "Daily", "weekly": "Weekly", "monthly": "Monthly"}.get(
        period_type, str(period_type).title()
    )
    story = [
        Paragraph("Incentive Report", styles["Title"]),
        Paragraph(f"Type: {type_label}", styles["Normal"]),
        Paragraph(f"Period: {period_label}", styles["Normal"]),
        Spacer(1, 14),
    ]

    table_data = [[str(h) for h in headers]]
    for row in rows:
        table_data.append([("—" if cell in ("", None) else str(cell)) for cell in row])

    if len(table_data) == 1:
        table_data.append(["No data"] + [""] * (len(headers) - 1))

    col_count = max(len(headers), 1)
    page_width = landscape(A4)[0] - 48
    if col_count == 1:
        widths = [page_width]
    else:
        widths = [page_width * 0.16] + [page_width * 0.84 / (col_count - 1)] * (
            col_count - 1
        )

    table = Table(table_data, colWidths=widths, repeatRows=1)
    style_commands = [
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
        ("ALIGN", (0, 0), (0, -1), "LEFT"),
    ]
    if rows and str(rows[-1][0]) == "Total":
        style_commands.extend(
            [
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#f8fafc")),
            ]
        )
    table.setStyle(TableStyle(style_commands))
    story.append(table)
    doc.build(story)
    buffer.seek(0)
    return pdf_response(filename, buffer)


def _styled_table(rows, col_widths, header=False):
    table = Table(rows, colWidths=col_widths, repeatRows=1 if header else 0)
    style = [
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    if header:
        style.append(("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")))
        style.append(("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"))
    table.setStyle(TableStyle(style))
    return table
