from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Sum

from masters.incentive_history import (
    period_segments,
    salary_as_of,
    settings_as_of,
)
from masters.models import Staff
from reports.models import DsrStaffLine
from reports.sales_report import month_date_range, monthly_period_label, quantize_money


PERIOD_TYPES = (
    ("daily", "Daily"),
    ("weekly", "Weekly"),
    ("monthly", "Monthly"),
)


def calc_target(salary, salary_times, period_type):
    salary = quantize_money(salary or 0)
    times = Decimal(str(salary_times or 0))
    monthly_target = salary * times
    if period_type == "daily":
        return quantize_money(monthly_target / Decimal("30"))
    if period_type == "weekly":
        return quantize_money(monthly_target / Decimal("4"))
    return quantize_money(monthly_target)


def calc_incentive(achieved, target, incentive_percent):
    """Incentive only when target achieved is equal to or more than target."""
    achieved = quantize_money(achieved or 0)
    target = quantize_money(target or 0)
    if target <= 0 or achieved < target:
        return Decimal("0.00")
    return quantize_money(
        achieved * Decimal(str(incentive_percent or 0)) / Decimal("100")
    )


def performance_in_range(staff_id, start, end):
    total = (
        DsrStaffLine.objects.filter(
            staff_id=staff_id,
            report__report_date__gte=start,
            report__report_date__lte=end,
        ).aggregate(total=Sum("amount"))["total"]
    )
    return quantize_money(total or 0)


def week_date_range(week_start):
    start = date.fromisoformat(week_start) if isinstance(week_start, str) else week_start
    end = start + timedelta(days=6)
    return start, end


def money_cell(value):
    return f"{quantize_money(value):.2f}"


def staff_period_result(staff, start, end, period_type):
    """
    Compute salary, target, achieved, incentive using historical rates.
    Period is split at salary / incentive-settings change dates.
    """
    period_days = (end - start).days + 1
    total_target = Decimal("0")
    total_achieved = Decimal("0")
    total_incentive = Decimal("0")
    salaries_used = []
    display_percent, _display_times = settings_as_of(end)
    percents = set()

    for seg_start, seg_end in period_segments(staff.pk, start, end):
        seg_days = (seg_end - seg_start).days + 1
        salary = quantize_money(salary_as_of(staff.pk, seg_start))
        # Prefer Staff Master when history still has zero (salary not versioned yet)
        if salary == 0 and staff.salary:
            salary = quantize_money(staff.salary)
        salaries_used.append(salary)
        incentive_percent, salary_times = settings_as_of(seg_start)
        percents.add(quantize_money(incentive_percent))

        full_target = calc_target(salary, salary_times, period_type)
        segment_target = quantize_money(
            full_target * Decimal(seg_days) / Decimal(period_days)
        )
        segment_achieved = performance_in_range(staff.pk, seg_start, seg_end)
        segment_incentive = calc_incentive(
            segment_achieved, segment_target, incentive_percent
        )

        total_target += segment_target
        total_achieved += segment_achieved
        total_incentive += segment_incentive

    # Salary column: Staff Master current salary, or historical if set
    display_salary = quantize_money(staff.salary or 0)
    if display_salary == 0 and salaries_used:
        display_salary = salaries_used[-1]
    # Target must match the salary used in calculation (historical segments)
    if total_target == 0 and display_salary > 0:
        pct, times = settings_as_of(end)
        total_target = calc_target(display_salary, times, period_type)
        total_incentive = calc_incentive(total_achieved, total_target, pct)
        display_percent = pct

    display_percent = (
        list(percents)[0] if len(percents) == 1 else quantize_money(display_percent)
    )
    mixed_percent = len(percents) > 1

    return {
        "salary": quantize_money(display_salary),
        "target": quantize_money(total_target),
        "achieved": quantize_money(total_achieved),
        "incentive_percent": display_percent,
        "mixed_percent": mixed_percent,
        "incentive": quantize_money(total_incentive),
    }


def build_incentive_report(
    *,
    period_type,
    staff_id=None,
    report_date=None,
    week_start=None,
    report_month=None,
):
    if period_type == "daily":
        start = end = date.fromisoformat(report_date)
        period_label = start.strftime("%d %b %Y")
    elif period_type == "weekly":
        start, end = week_date_range(week_start)
        period_label = f"{start.isoformat()} to {end.isoformat()}"
    else:
        start, end = month_date_range(report_month)
        period_label = monthly_period_label(report_month)

    staff_qs = Staff.objects.filter(active=True).order_by("name")
    if staff_id:
        staff_qs = staff_qs.filter(pk=staff_id)

    headers = [
        "Staff",
        "Salary (Rs)",
        "Target (Rs)",
        "Target achieved (Rs)",
        "Achievement %",
        "Incentive %",
        "Incentive (Rs)",
        "Target met",
    ]
    rows = []
    totals = {
        "salary": Decimal("0"),
        "target": Decimal("0"),
        "achieved": Decimal("0"),
        "incentive": Decimal("0"),
    }

    for staff in staff_qs:
        result = staff_period_result(staff, start, end, period_type)
        salary = result["salary"]
        target = result["target"]
        achieved = result["achieved"]
        incentive = result["incentive"]
        incentive_percent = result["incentive_percent"]

        if salary == 0 and achieved == 0:
            continue

        achievement_pct = (
            quantize_money(achieved * Decimal("100") / target) if target > 0 else Decimal("0")
        )
        target_met = "Yes" if achieved >= target and target > 0 else "No"
        percent_display = (
            "Mixed" if result["mixed_percent"] else float(quantize_money(incentive_percent))
        )

        totals["salary"] += salary
        totals["target"] += target
        totals["achieved"] += achieved
        totals["incentive"] += incentive

        rows.append(
            [
                staff.name,
                money_cell(salary),
                money_cell(target),
                money_cell(achieved),
                money_cell(achievement_pct),
                percent_display if percent_display == "Mixed" else money_cell(incentive_percent),
                money_cell(incentive),
                target_met,
            ]
        )

    missing_salary = any(
        Decimal(str(row[1])) == 0 and Decimal(str(row[3])) > 0 for row in rows
    )

    if rows:
        overall_pct = (
            quantize_money(totals["achieved"] * Decimal("100") / totals["target"])
            if totals["target"] > 0
            else Decimal("0")
        )
        rows.append(
            [
                "Total",
                money_cell(totals["salary"]),
                money_cell(totals["target"]),
                money_cell(totals["achieved"]),
                money_cell(overall_pct),
                "",
                money_cell(totals["incentive"]),
                "",
            ]
        )

    return headers, rows, period_label, missing_salary
