import io

from django.http import HttpResponse
from openpyxl import Workbook

from reports.dsr_validation import INCOME_FIELD_NAMES
from reports.sales_report import calc_avb, quantize_money, total_income_from_data


def excel_response(filename, headers, rows):
    wb = Workbook()
    ws = wb.active
    ws.append(headers)
    for row in rows:
        ws.append(row)
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    response = HttpResponse(
        buffer.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


def build_dsr_display_excel(filename, display):
    rows = [
        ["Branch", display["branch_name"]],
        ["Period", display["period_label"]],
        [],
        ["Income", ""],
        ["Net Service income", float(quantize_money(display["net_service_income"]))],
        ["Membership Card", float(quantize_money(display["membership_card"]))],
        ["Ear Piercing", float(quantize_money(display["ear_piercing"]))],
        ["Other Income", float(quantize_money(display["other_income"]))],
        ["Product Sale 18%", float(quantize_money(display["product_sale_18"]))],
        ["Product Sale 5%", float(quantize_money(display["product_sale_5"]))],
        ["GST", float(quantize_money(display["gst"]))],
        ["Bridal Advance", float(quantize_money(display["bridal_advance"]))],
        ["Total Income", float(quantize_money(total_income_from_data(display)))],
        [],
        ["Walk Ins", "Count", "Income", "AVB"],
        [
            "Male",
            display["male_walkins"],
            float(quantize_money(display["male_income"])),
            float(calc_avb(display["male_income"], display["male_walkins"]) or 0),
        ],
        [
            "Female",
            display["female_walkins"],
            float(quantize_money(display["female_income"])),
            float(calc_avb(display["female_income"], display["female_walkins"]) or 0),
        ],
        [
            "Kids",
            display["kids_walkins"],
            float(quantize_money(display["kids_income"])),
            float(calc_avb(display["kids_income"], display["kids_walkins"]) or 0),
        ],
        [],
        ["Mode of Payment", ""],
        ["Card Payment", float(quantize_money(display["card_payment"]))],
        ["UPI", float(quantize_money(display["upi_payment"]))],
        ["Cash Payment", float(quantize_money(display["cash_payment"]))],
        [],
        ["Marketing Updates", ""],
        ["No. of calls done", display["calls_done"]],
        ["Zooty Appointment", display["zooty_appointment"]],
        ["By Google appointment", display["google_appointment"]],
        ["Just dial", display["just_dial"]],
        ["Broadcast", display["broadcast"]],
        ["No of New Clients", display["new_clients"]],
        [],
        ["Staff Performance", "Amount"],
    ]
    for line in display["staff_lines"]:
        rows.append([line["staff_name"], float(quantize_money(line["amount"]))])

    return excel_response(filename, ["Field", "Value"], rows)
