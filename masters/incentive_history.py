from datetime import date, timedelta
from decimal import Decimal

from django.utils import timezone

from masters.models import (
    IncentiveSettings,
    IncentiveSettingsVersion,
    Staff,
    StaffSalaryVersion,
)

SEED_DATE = date(2000, 1, 1)


def settings_as_of(as_of_date):
    """Return (incentive_percent, salary_times) effective on as_of_date."""
    if isinstance(as_of_date, str):
        as_of_date = date.fromisoformat(as_of_date)
    version = (
        IncentiveSettingsVersion.objects.filter(effective_from__lte=as_of_date)
        .order_by("-effective_from", "-pk")
        .first()
    )
    if version:
        return version.incentive_percent, version.salary_times
    solo = IncentiveSettings.get_solo()
    return solo.incentive_percent, solo.salary_times


def salary_as_of(staff_id, as_of_date):
    """Return staff salary effective on as_of_date (from history, else Staff Master)."""
    if isinstance(as_of_date, str):
        as_of_date = date.fromisoformat(as_of_date)
    staff = Staff.objects.filter(pk=staff_id).first()
    if not staff:
        return Decimal("0")

    version = (
        StaffSalaryVersion.objects.filter(
            staff_id=staff_id,
            effective_from__lte=as_of_date,
        )
        .order_by("-effective_from", "-pk")
        .first()
    )
    if not version:
        return staff.salary or Decimal("0")

    # Seed/history is still zero but Staff Master has a salary and no real
    # non-zero version exists yet — use Staff Master.
    has_nonzero_history = StaffSalaryVersion.objects.filter(
        staff_id=staff_id, salary__gt=0
    ).exists()
    if version.salary == 0 and staff.salary and staff.salary > 0 and not has_nonzero_history:
        return staff.salary

    return version.salary


def record_incentive_settings_version(incentive_percent, salary_times, effective_from=None):
    effective_from = effective_from or timezone.localdate()
    incentive_percent = Decimal(str(incentive_percent))
    salary_times = Decimal(str(salary_times))

    versions = list(IncentiveSettingsVersion.objects.order_by("effective_from", "pk"))
    if not versions:
        return IncentiveSettingsVersion.objects.create(
            incentive_percent=incentive_percent,
            salary_times=salary_times,
            effective_from=SEED_DATE,
        )

    # First real setup: replace placeholder seed so rules apply to past periods.
    if len(versions) == 1 and versions[0].effective_from <= SEED_DATE:
        first = versions[0]
        first.incentive_percent = incentive_percent
        first.salary_times = salary_times
        first.save(update_fields=["incentive_percent", "salary_times"])
        return first

    current_pct, current_times = settings_as_of(effective_from)
    if (
        Decimal(str(current_pct)) == incentive_percent
        and Decimal(str(current_times)) == salary_times
    ):
        return None
    return IncentiveSettingsVersion.objects.create(
        incentive_percent=incentive_percent,
        salary_times=salary_times,
        effective_from=effective_from,
    )


def record_staff_salary_version(staff, salary, effective_from=None):
    effective_from = effective_from or timezone.localdate()
    salary = Decimal(str(salary))

    versions = list(
        StaffSalaryVersion.objects.filter(staff=staff).order_by("effective_from", "pk")
    )
    if not versions:
        return StaffSalaryVersion.objects.create(
            staff=staff,
            salary=salary,
            effective_from=SEED_DATE,
        )

    # First real salary: update seed so it applies to all past incentive periods.
    if all(v.salary == 0 for v in versions):
        first = versions[0]
        first.salary = salary
        first.save(update_fields=["salary"])
        StaffSalaryVersion.objects.filter(staff=staff).exclude(pk=first.pk).delete()
        return first

    current = salary_as_of(staff.pk, effective_from)
    if Decimal(str(current)) == salary:
        return None
    return StaffSalaryVersion.objects.create(
        staff=staff,
        salary=salary,
        effective_from=effective_from,
    )


def change_dates_in_range(staff_id, start, end):
    """Dates in (start, end] where salary or incentive settings change."""
    dates = set()
    for d in IncentiveSettingsVersion.objects.filter(
        effective_from__gt=start,
        effective_from__lte=end,
    ).values_list("effective_from", flat=True):
        dates.add(d)
    for d in StaffSalaryVersion.objects.filter(
        staff_id=staff_id,
        effective_from__gt=start,
        effective_from__lte=end,
    ).values_list("effective_from", flat=True):
        dates.add(d)
    return sorted(dates)


def period_segments(staff_id, start, end):
    """Return (seg_start, seg_end) pairs covering [start, end] with constant rates."""
    points = [start] + change_dates_in_range(staff_id, start, end)
    points.append(end + timedelta(days=1))
    segments = []
    for i in range(len(points) - 1):
        seg_start = points[i]
        seg_end = points[i + 1] - timedelta(days=1)
        if seg_start <= seg_end:
            segments.append((seg_start, seg_end))
    return segments
