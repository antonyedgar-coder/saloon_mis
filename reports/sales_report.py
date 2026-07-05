from calendar import monthrange
from collections import defaultdict
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from django.db.models import Sum

from reports.dsr_validation import INCOME_FIELD_NAMES
from reports.models import DailySalesReport, DsrStaffLine

DECIMAL_SUM_FIELDS = INCOME_FIELD_NAMES + (
    "male_income",
    "female_income",
    "kids_income",
    "card_payment",
    "upi_payment",
    "cash_payment",
)

INT_SUM_FIELDS = (
    "male_walkins",
    "female_walkins",
    "kids_walkins",
    "calls_done",
    "zooty_appointment",
    "google_appointment",
    "just_dial",
    "broadcast",
    "new_clients",
)

FY_MONTHS = (
    (4, "April"),
    (5, "May"),
    (6, "June"),
    (7, "July"),
    (8, "August"),
    (9, "September"),
    (10, "October"),
    (11, "November"),
    (12, "December"),
    (1, "January"),
    (2, "February"),
    (3, "March"),
)


TWOPLACES = Decimal("0.01")


def quantize_money(value):
    if value is None:
        return Decimal("0.00")
    return Decimal(value).quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def format_money(value):
    return f"{quantize_money(value):,.2f}"


def calc_avb(income, walkins):
    if not walkins:
        return None
    return (Decimal(income) / Decimal(walkins)).quantize(Decimal("0.01"))


def product_sales_total(data):
    return data.get("product_sale_18", Decimal("0")) + data.get(
        "product_sale_5", Decimal("0")
    )


def total_income_from_data(data):
    return sum(data.get(name, Decimal("0")) for name in INCOME_FIELD_NAMES)


MONTH_LABELS = (
    (1, "January"),
    (2, "February"),
    (3, "March"),
    (4, "April"),
    (5, "May"),
    (6, "June"),
    (7, "July"),
    (8, "August"),
    (9, "September"),
    (10, "October"),
    (11, "November"),
    (12, "December"),
)

MIN_REPORT_YEAR = 2025
MIN_FINANCIAL_YEAR_START = 2025


def calendar_year_choices(min_year=MIN_REPORT_YEAR):
    today = date.today()
    return [str(year) for year in range(today.year, min_year - 1, -1)]


def financial_year_choices(min_start_year=MIN_FINANCIAL_YEAR_START):
    today = date.today()
    if today.month >= 4:
        current_start = today.year
    else:
        current_start = today.year - 1
    choices = []
    for start in range(current_start + 1, min_start_year - 1, -1):
        end_short = (start + 1) % 100
        label = f"{start}-{end_short:02d}"
        choices.append((str(start), label))
    return choices


def financial_year_range(fy_start_year):
    start = int(fy_start_year)
    return date(start, 4, 1), date(start + 1, 3, 31)


def aggregate_staff_lines(queryset):
    totals = defaultdict(Decimal)
    lines = (
        DsrStaffLine.objects.filter(report__in=queryset)
        .select_related("staff")
        .order_by("staff__name")
    )
    for line in lines:
        totals[line.staff.name] += line.amount
    return [
        {"staff_name": name, "amount": quantize_money(amount)}
        for name, amount in sorted(totals.items())
    ]


def round_aggregated_data(data):
    rounded = {"days_count": data["days_count"]}
    for field in DECIMAL_SUM_FIELDS:
        rounded[field] = quantize_money(data[field])
    for field in INT_SUM_FIELDS:
        rounded[field] = int(data[field] or 0)
    rounded["staff_lines"] = [
        {"staff_name": line["staff_name"], "amount": quantize_money(line["amount"])}
        for line in data["staff_lines"]
    ]
    return rounded


def aggregate_dsr_queryset(queryset):
    if not queryset.exists():
        return None

    aggregates = {}
    for field in DECIMAL_SUM_FIELDS:
        aggregates[field] = Sum(field)
    for field in INT_SUM_FIELDS:
        aggregates[field] = Sum(field)

    totals = queryset.aggregate(**aggregates)
    data = {
        field: totals[field] or (0 if field in INT_SUM_FIELDS else Decimal("0"))
        for field in DECIMAL_SUM_FIELDS + INT_SUM_FIELDS
    }
    data["staff_lines"] = aggregate_staff_lines(queryset)
    data["days_count"] = queryset.count()
    return round_aggregated_data(data)


def enrich_display(display):
    male_w = display["male_walkins"]
    female_w = display["female_walkins"]
    kids_w = display["kids_walkins"]
    total_w = male_w + female_w + kids_w
    total_income_val = total_income_from_data(display)
    total_walkin_income = (
        display["male_income"] + display["female_income"] + display["kids_income"]
    )
    display["total_income"] = quantize_money(total_income_val)
    display["total_walkins"] = total_w
    display["total_walkin_income"] = quantize_money(total_walkin_income)
    display["male_avb"] = calc_avb(display["male_income"], male_w)
    display["female_avb"] = calc_avb(display["female_income"], female_w)
    display["kids_avb"] = calc_avb(display["kids_income"], kids_w)
    display["total_avb"] = calc_avb(total_walkin_income, total_w)
    display["staff_total"] = quantize_money(
        sum((line["amount"] for line in display["staff_lines"]), Decimal("0"))
    )
    display["payment_total"] = quantize_money(
        display["card_payment"] + display["upi_payment"] + display["cash_payment"]
    )
    return display


def report_to_display_values(report):
    display = {
        "branch_name": report.branch.name,
        "period_label": report.report_date.strftime("%d %b %Y"),
        "net_service_income": report.net_service_income,
        "membership_card": report.membership_card,
        "ear_piercing": report.ear_piercing,
        "other_income": report.other_income,
        "product_sale_18": report.product_sale_18,
        "product_sale_5": report.product_sale_5,
        "gst": report.gst,
        "bridal_advance": report.bridal_advance,
        "male_walkins": report.male_walkins,
        "male_income": report.male_income,
        "female_walkins": report.female_walkins,
        "female_income": report.female_income,
        "kids_walkins": report.kids_walkins,
        "kids_income": report.kids_income,
        "card_payment": report.card_payment,
        "upi_payment": report.upi_payment,
        "cash_payment": report.cash_payment,
        "calls_done": report.calls_done,
        "zooty_appointment": report.zooty_appointment,
        "google_appointment": report.google_appointment,
        "just_dial": report.just_dial,
        "status_story": report.status_story,
        "broadcast": report.broadcast,
        "google_reviews_request": report.google_reviews_request,
        "new_clients": report.new_clients,
        "staff_lines": [
            {
                "staff_name": line.staff.name,
                "amount": line.amount,
                "mem_card": line.mem_card,
                "makeup": line.makeup,
                "google_review_with_photo": line.google_review_with_photo,
                "google_review_without_photo": line.google_review_without_photo,
                "ear_piercing": line.ear_piercing,
                "watts": line.watts,
                "ot": line.ot,
            }
            for line in report.staff_lines.select_related("staff")
        ],
    }
    return enrich_display(display)


def aggregated_to_display_values(data, branch_name, period_label):
    display = {
        "branch_name": branch_name,
        "period_label": period_label,
        **{field: data[field] for field in DECIMAL_SUM_FIELDS + INT_SUM_FIELDS},
        "status_story": "",
        "google_reviews_request": "",
        "staff_lines": data["staff_lines"],
    }
    return enrich_display(display)


def build_yearly_rows(queryset, fy_start_year):
    headers = [
        "Month",
        "Net Service Income",
        "Product Sales",
        "GST",
        "Total Income",
        "Men Walk-in",
        "Female Walk-in",
        "Kids Walk-in",
        "Total Walk-in",
        "Avg Men Bill",
        "Avg Female Bill",
        "Avg Kids Bill",
        "Total Bill Value",
    ]
    rows = []
    start_year = int(fy_start_year)

    for month_num, month_name in FY_MONTHS:
        year = start_year if month_num >= 4 else start_year + 1
        month_qs = queryset.filter(report_date__year=year, report_date__month=month_num)
        agg = aggregate_dsr_queryset(month_qs)
        label = f"{month_name} {year}"

        if not agg:
            rows.append([label, 0, 0, 0, 0, 0, 0, 0, 0, "", "", "", ""])
            continue

        male_w = agg["male_walkins"]
        female_w = agg["female_walkins"]
        kids_w = agg["kids_walkins"]
        total_w = male_w + female_w + kids_w
        total_walkin_income = (
            agg["male_income"] + agg["female_income"] + agg["kids_income"]
        )

        rows.append([
            label,
            float(agg["net_service_income"]),
            float(product_sales_total(agg)),
            float(agg["gst"]),
            float(total_income_from_data(agg)),
            male_w,
            female_w,
            kids_w,
            total_w,
            float(calc_avb(agg["male_income"], male_w)) if male_w else "",
            float(calc_avb(agg["female_income"], female_w)) if female_w else "",
            float(calc_avb(agg["kids_income"], kids_w)) if kids_w else "",
            float(calc_avb(total_walkin_income, total_w)) if total_w else "",
        ])

    return headers, rows


def monthly_period_label(month_value):
    year, month = map(int, month_value.split("-"))
    return date(year, month, 1).strftime("%B %Y")


def month_date_range(month_value):
    year, month = map(int, month_value.split("-"))
    last_day = monthrange(year, month)[1]
    return date(year, month, 1), date(year, month, last_day)


def build_report_month(year, month_num):
    return f"{int(year)}-{int(month_num):02d}"


def parse_report_month_params(report_month, report_year, report_month_num):
    if report_year and report_month_num:
        return build_report_month(report_year, report_month_num)
    if report_month and "-" in report_month:
        return report_month
    today = date.today()
    return build_report_month(today.year, today.month)
