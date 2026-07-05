from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Sum
from django.db.models.functions import TruncDate

from inventory.models import BranchOutwardLine, BranchOutwardType
from masters.incentive_history import (
    calc_retail_incentive,
    period_has_incentive,
    period_segments,
    retail_slabs_as_of,
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


def calc_target(salary, salary_times):
    salary = quantize_money(salary or 0)
    times = Decimal(str(salary_times or 0))
    return quantize_money(salary * times)


def calc_service_incentive(achieved, target, incentive_percent):
    achieved = quantize_money(achieved or 0)
    target = quantize_money(target or 0)
    if target <= 0 or achieved < target:
        return Decimal("0.00")
    return quantize_money(
        achieved * Decimal(str(incentive_percent or 0)) / Decimal("100")
    )


def service_achieved_in_range(staff_id, start, end):
    total = (
        DsrStaffLine.objects.filter(
            staff_id=staff_id,
            report__report_date__gte=start,
            report__report_date__lte=end,
        ).aggregate(total=Sum("amount"))["total"]
    )
    return quantize_money(total or 0)


def retail_sales_in_range(staff_id, start, end):
    total = (
        BranchOutwardLine.objects.filter(
            staff_id=staff_id,
            branch_outward__type=BranchOutwardType.RETAIL_SALE,
        )
        .annotate(outward_date=TruncDate("branch_outward__date"))
        .filter(outward_date__gte=start, outward_date__lte=end)
        .aggregate(total=Sum("amount"))["total"]
    )
    return quantize_money(total or 0)


def staff_dsr_metrics(staff_id, start, end):
    totals = DsrStaffLine.objects.filter(
        staff_id=staff_id,
        report__report_date__gte=start,
        report__report_date__lte=end,
    ).aggregate(
        makeup=Sum("makeup"),
        google_review_with_photo=Sum("google_review_with_photo"),
        google_review_without_photo=Sum("google_review_without_photo"),
        ear_piercing=Sum("ear_piercing"),
        watts=Sum("watts"),
        mem_card=Sum("mem_card"),
        ot=Sum("ot"),
    )
    return {
        "makeup": totals.get("makeup") or Decimal("0"),
        "google_review_with_photo": totals.get("google_review_with_photo") or 0,
        "google_review_without_photo": totals.get("google_review_without_photo") or 0,
        "ear_piercing": totals.get("ear_piercing") or 0,
        "watts": totals.get("watts") or 0,
        "mem_card": totals.get("mem_card") or 0,
        "ot": totals.get("ot") or Decimal("0"),
    }


def calc_staff_performance_incentive(metrics, config):
    if not config.get("staff_performance_enabled"):
        return Decimal("0.00")
    total = Decimal("0")
    total += quantize_money(metrics.get("makeup") or 0) * Decimal(
        str(config.get("makeup_percent") or 0)
    ) / Decimal("100")
    total += Decimal(str(metrics.get("google_review_with_photo") or 0)) * Decimal(
        str(config.get("google_review_with_photo_incentive") or 0)
    )
    total += Decimal(str(metrics.get("google_review_without_photo") or 0)) * Decimal(
        str(config.get("google_review_without_photo_incentive") or 0)
    )
    total += Decimal(str(metrics.get("ear_piercing") or 0)) * Decimal(
        str(config.get("ear_piercing_incentive") or 0)
    )
    total += Decimal(str(metrics.get("watts") or 0)) * Decimal(
        str(config.get("watts_incentive") or 0)
    )
    total += Decimal(str(metrics.get("mem_card") or 0)) * Decimal(
        str(config.get("membership_card_incentive") or 0)
    )
    total += Decimal(str(metrics.get("ot") or 0)) * Decimal(
        str(config.get("ot_incentive") or 0)
    )
    return quantize_money(total)


def week_date_range(week_start):
    start = date.fromisoformat(week_start) if isinstance(week_start, str) else week_start
    end = start + timedelta(days=6)
    return start, end


def money_cell(value):
    return f"{quantize_money(value):.2f}"


def staff_period_result(staff, start, end, period_type):
    period_days = (end - start).days + 1
    totals = {
        "salary": quantize_money(staff.salary or 0),
        "service_target": Decimal("0"),
        "service_achieved": Decimal("0"),
        "service_incentive": Decimal("0"),
        "retail_sales": Decimal("0"),
        "retail_incentive": Decimal("0"),
        "staff_perf_incentive": Decimal("0"),
        "total_incentive": Decimal("0"),
    }

    for seg_start, seg_end in period_segments(staff.pk, start, end, period_type):
        seg_days = (seg_end - seg_start).days + 1
        config = settings_as_of(seg_start, period_type)
        slabs = retail_slabs_as_of(seg_start, period_type)
        salary = quantize_money(salary_as_of(staff.pk, seg_start))
        if salary == 0 and staff.salary:
            salary = quantize_money(staff.salary)
        if salary > 0:
            totals["salary"] = salary

        if config.get("service_enabled"):
            full_target = calc_target(salary, config.get("salary_times"))
            segment_target = quantize_money(
                full_target * Decimal(seg_days) / Decimal(period_days)
            )
            segment_achieved = service_achieved_in_range(staff.pk, seg_start, seg_end)
            totals["service_target"] += segment_target
            totals["service_achieved"] += segment_achieved
            totals["service_incentive"] += calc_service_incentive(
                segment_achieved,
                segment_target,
                config.get("incentive_percent"),
            )

        if config.get("retail_enabled"):
            segment_sales = retail_sales_in_range(staff.pk, seg_start, seg_end)
            totals["retail_sales"] += segment_sales
            totals["retail_incentive"] += calc_retail_incentive(segment_sales, slabs)

        if config.get("staff_performance_enabled"):
            metrics = staff_dsr_metrics(staff.pk, seg_start, seg_end)
            totals["staff_perf_incentive"] += calc_staff_performance_incentive(
                metrics, config
            )

    totals["total_incentive"] = quantize_money(
        totals["service_incentive"]
        + totals["retail_incentive"]
        + totals["staff_perf_incentive"]
    )
    for key in totals:
        totals[key] = quantize_money(totals[key])
    return totals


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

    config = settings_as_of(end, period_type)
    slabs = retail_slabs_as_of(end, period_type)
    if not period_has_incentive(config, slabs):
        headers = [
            "Staff",
            "Salary (Rs)",
            "Service target (Rs)",
            "Service achieved (Rs)",
            "Service incentive (Rs)",
            "Retail sales (Rs)",
            "Retail incentive (Rs)",
            "Staff perf incentive (Rs)",
            "Total incentive (Rs)",
        ]
        return headers, [], period_label, False

    staff_qs = Staff.objects.filter(active=True).order_by("name")
    if staff_id:
        staff_qs = staff_qs.filter(pk=staff_id)

    headers = [
        "Staff",
        "Salary (Rs)",
        "Service target (Rs)",
        "Service achieved (Rs)",
        "Service incentive (Rs)",
        "Retail sales (Rs)",
        "Retail incentive (Rs)",
        "Staff perf incentive (Rs)",
        "Total incentive (Rs)",
    ]
    rows = []
    totals = {key: Decimal("0") for key in (
        "salary",
        "service_target",
        "service_achieved",
        "service_incentive",
        "retail_sales",
        "retail_incentive",
        "staff_perf_incentive",
        "total_incentive",
    )}

    for staff in staff_qs:
        result = staff_period_result(staff, start, end, period_type)
        if (
            result["service_achieved"] == 0
            and result["retail_sales"] == 0
            and result["staff_perf_incentive"] == 0
            and result["total_incentive"] == 0
        ):
            continue

        for key in totals:
            totals[key] += result[key]

        rows.append(
            [
                staff.name,
                money_cell(result["salary"]),
                money_cell(result["service_target"]),
                money_cell(result["service_achieved"]),
                money_cell(result["service_incentive"]),
                money_cell(result["retail_sales"]),
                money_cell(result["retail_incentive"]),
                money_cell(result["staff_perf_incentive"]),
                money_cell(result["total_incentive"]),
            ]
        )

    missing_salary = any(
        Decimal(str(row[1])) == 0
        and (
            Decimal(str(row[3])) > 0
            or Decimal(str(row[5])) > 0
            or Decimal(str(row[7])) > 0
        )
        for row in rows
    )

    if rows:
        rows.append(
            [
                "Total",
                money_cell(totals["salary"]),
                money_cell(totals["service_target"]),
                money_cell(totals["service_achieved"]),
                money_cell(totals["service_incentive"]),
                money_cell(totals["retail_sales"]),
                money_cell(totals["retail_incentive"]),
                money_cell(totals["staff_perf_incentive"]),
                money_cell(totals["total_incentive"]),
            ]
        )

    return headers, rows, period_label, missing_salary
