from collections import defaultdict
from datetime import date
from decimal import Decimal

from django.db.models import Count, Sum

from reports.models import DsrStaffLine
from reports.sales_report import (
    FY_MONTHS,
    financial_year_range,
    month_date_range,
    monthly_period_label,
    quantize_money,
)


PERIOD_TYPES = (
    ("range", "Date range"),
    ("monthly", "Month wise"),
    ("yearly", "Year wise"),
)


def staff_lines_queryset(staff_id=None, start=None, end=None):
    """Staff performance is always across all branches."""
    qs = DsrStaffLine.objects.select_related("staff", "report")
    if staff_id:
        qs = qs.filter(staff_id=staff_id)
    if start:
        qs = qs.filter(report__report_date__gte=start)
    if end:
        qs = qs.filter(report__report_date__lte=end)
    return qs


def build_summary_rows(queryset):
    headers = [
        "Staff",
        "Monthly salary (Rs)",
        "Performance (Rs)",
        "Days",
    ]
    aggregates = (
        queryset.values("staff_id", "staff__name", "staff__salary")
        .annotate(
            performance=Sum("amount"),
            days=Count("report__report_date", distinct=True),
        )
        .order_by("staff__name")
    )

    rows = []
    total_performance = Decimal("0")
    total_days = 0
    for row in aggregates:
        performance = quantize_money(row["performance"] or 0)
        days = int(row["days"] or 0)
        total_performance += performance
        total_days += days
        rows.append(
            [
                row["staff__name"],
                float(quantize_money(row["staff__salary"] or 0)),
                float(performance),
                days,
            ]
        )

    if rows:
        rows.append(
            [
                "Total",
                "",
                float(quantize_money(total_performance)),
                total_days,
            ]
        )
    return headers, rows


def build_yearly_rows(queryset, financial_year):
    month_labels = [label for _, label in FY_MONTHS]
    headers = ["Staff", "Monthly salary (Rs)"] + month_labels + ["Total"]

    fy_start, fy_end = financial_year_range(financial_year)
    month_keys = []
    for month_num, _label in FY_MONTHS:
        year = int(financial_year) if month_num >= 4 else int(financial_year) + 1
        month_keys.append((year, month_num))

    staff_data = defaultdict(
        lambda: {
            "name": "",
            "salary": Decimal("0"),
            "months": defaultdict(lambda: Decimal("0")),
        }
    )

    for line in queryset.filter(
        report__report_date__gte=fy_start,
        report__report_date__lte=fy_end,
    ).select_related("staff", "report"):
        key = line.staff_id
        entry = staff_data[key]
        entry["name"] = line.staff.name
        entry["salary"] = quantize_money(line.staff.salary or 0)
        report_date = line.report.report_date
        entry["months"][(report_date.year, report_date.month)] += line.amount

    rows = []
    month_totals = [Decimal("0") for _ in month_keys]
    grand_total = Decimal("0")

    for staff_id in sorted(staff_data.keys(), key=lambda pk: staff_data[pk]["name"].lower()):
        entry = staff_data[staff_id]
        row = [entry["name"], float(entry["salary"])]
        staff_total = Decimal("0")
        for idx, month_key in enumerate(month_keys):
            amount = quantize_money(entry["months"].get(month_key, Decimal("0")))
            staff_total += amount
            month_totals[idx] += amount
            row.append(float(amount) if amount else "")
        grand_total += staff_total
        row.append(float(quantize_money(staff_total)))
        rows.append(row)

    if rows:
        total_row = ["Total", ""]
        for amount in month_totals:
            total_row.append(float(quantize_money(amount)) if amount else "")
        total_row.append(float(quantize_money(grand_total)))
        rows.append(total_row)

    return headers, rows


def period_label_for(period_type, *, from_date, to_date, report_month, financial_year, fy_choices):
    if period_type == "range":
        return f"{from_date} to {to_date}"
    if period_type == "monthly":
        return monthly_period_label(report_month)
    fy_label = dict(fy_choices).get(financial_year, financial_year)
    return f"Financial year {fy_label}"


def build_staff_performance_report(
    *,
    period_type,
    staff_id=None,
    from_date=None,
    to_date=None,
    report_month=None,
    financial_year=None,
):
    if period_type == "range":
        start = date.fromisoformat(from_date)
        end = date.fromisoformat(to_date)
        qs = staff_lines_queryset(staff_id, start, end)
        return build_summary_rows(qs)

    if period_type == "monthly":
        start, end = month_date_range(report_month)
        qs = staff_lines_queryset(staff_id, start, end)
        return build_summary_rows(qs)

    if period_type == "yearly":
        start, end = financial_year_range(financial_year)
        qs = staff_lines_queryset(staff_id, start, end)
        return build_yearly_rows(qs, financial_year)

    return [], []
