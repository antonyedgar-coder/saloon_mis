from datetime import date, timedelta
from decimal import Decimal

from django.utils import timezone

from masters.models import (
    IncentivePeriodProfile,
    IncentivePeriodType,
    IncentiveSettings,
    IncentiveSettingsVersion,
    RetailSaleIncentiveSlab,
    RetailSaleIncentiveSlabVersion,
    Staff,
    StaffSalaryVersion,
)

SEED_DATE = date(2000, 1, 1)
PERIOD_TYPES = tuple(IncentivePeriodType.values)


def _config_dict(source):
    return {
        "service_enabled": source.service_enabled,
        "incentive_percent": source.incentive_percent,
        "salary_times": source.salary_times,
        "retail_enabled": source.retail_enabled,
        "staff_performance_enabled": source.staff_performance_enabled,
        "makeup_percent": source.makeup_percent,
        "google_review_with_photo_incentive": source.google_review_with_photo_incentive,
        "google_review_without_photo_incentive": source.google_review_without_photo_incentive,
        "ear_piercing_incentive": source.ear_piercing_incentive,
        "watts_incentive": source.watts_incentive,
        "membership_card_incentive": source.membership_card_incentive,
        "ot_incentive": source.ot_incentive,
    }


def settings_as_of(as_of_date, period_type):
    """Return incentive config effective on as_of_date for a report period type."""
    if isinstance(as_of_date, str):
        as_of_date = date.fromisoformat(as_of_date)
    version = (
        IncentiveSettingsVersion.objects.filter(
            effective_from__lte=as_of_date,
            period_type=period_type,
        )
        .order_by("-effective_from", "-pk")
        .first()
    )
    if version:
        return _config_dict(version)
    IncentivePeriodProfile.ensure_all()
    return _config_dict(IncentivePeriodProfile.get_for(period_type))


def retail_slabs_as_of(as_of_date, period_type):
    """Return retail slabs effective on as_of_date for a report period type."""
    if isinstance(as_of_date, str):
        as_of_date = date.fromisoformat(as_of_date)
    version = (
        IncentiveSettingsVersion.objects.filter(
            effective_from__lte=as_of_date,
            period_type=period_type,
        )
        .order_by("-effective_from", "-pk")
        .prefetch_related("retail_slabs")
        .first()
    )
    if version:
        return list(version.retail_slabs.all())
    return list(RetailSaleIncentiveSlab.objects.filter(period_type=period_type))


def period_has_incentive(config, slabs):
    """True when any enabled category has configured values for this period type."""
    if config.get("service_enabled") and (
        Decimal(str(config.get("incentive_percent") or 0)) > 0
        or Decimal(str(config.get("salary_times") or 0)) > 0
    ):
        return True
    if config.get("retail_enabled") and any(
        Decimal(str(getattr(s, "incentive_value", 0) or 0)) > 0 for s in slabs
    ):
        return True
    if config.get("staff_performance_enabled"):
        staff_fields = (
            "makeup_percent",
            "google_review_with_photo_incentive",
            "google_review_without_photo_incentive",
            "ear_piercing_incentive",
            "watts_incentive",
            "membership_card_incentive",
            "ot_incentive",
        )
        if any(Decimal(str(config.get(field) or 0)) > 0 for field in staff_fields):
            return True
    return False


def calc_retail_incentive(sale_amount, slabs):
    """Return incentive value for a retail sale amount using configured slabs."""
    amount = Decimal(str(sale_amount or 0))
    if amount <= 0:
        return Decimal("0")
    for slab in sorted(slabs, key=lambda s: (s.sort_order, s.sale_from, s.pk)):
        if amount < slab.sale_from:
            continue
        if slab.sale_to is None or amount <= slab.sale_to:
            return Decimal(str(slab.incentive_value))
    return Decimal("0")


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

    has_nonzero_history = StaffSalaryVersion.objects.filter(
        staff_id=staff_id, salary__gt=0
    ).exists()
    if version.salary == 0 and staff.salary and staff.salary > 0 and not has_nonzero_history:
        return staff.salary

    return version.salary


def _config_changed(current, new_values):
    for key, value in new_values.items():
        current_value = current.get(key)
        if isinstance(current_value, bool) or isinstance(value, bool):
            if bool(current_value) != bool(value):
                return True
        elif Decimal(str(current_value or 0)) != Decimal(str(value or 0)):
            return True
    return False


def _slabs_changed(existing_slabs, new_rows):
    existing = [
        (
            Decimal(str(s.sale_from)),
            None if s.sale_to is None else Decimal(str(s.sale_to)),
            Decimal(str(s.incentive_value)),
        )
        for s in existing_slabs
    ]
    parsed = []
    for row in new_rows:
        sale_from = Decimal(str(row.get("sale_from") or 0))
        sale_to_raw = row.get("sale_to")
        sale_to = Decimal(str(sale_to_raw)) if str(sale_to_raw).strip() else None
        incentive_value = Decimal(str(row.get("incentive_value") or 0))
        if sale_to is not None and sale_to < sale_from:
            continue
        parsed.append((sale_from, sale_to, incentive_value))
    return existing != parsed


def _copy_slabs_to_version(version, period_type):
    RetailSaleIncentiveSlabVersion.objects.filter(version=version).delete()
    for slab in RetailSaleIncentiveSlab.objects.filter(period_type=period_type):
        RetailSaleIncentiveSlabVersion.objects.create(
            version=version,
            sale_from=slab.sale_from,
            sale_to=slab.sale_to,
            incentive_value=slab.incentive_value,
            sort_order=slab.sort_order,
        )


def record_period_settings_version(config, slab_rows, effective_from=None):
    effective_from = effective_from or timezone.localdate()
    period_type = config["period_type"]
    values = {key: config[key] for key in config if key != "period_type"}

    versions = list(
        IncentiveSettingsVersion.objects.filter(period_type=period_type).order_by(
            "effective_from", "pk"
        )
    )
    if not versions:
        version = IncentiveSettingsVersion.objects.create(
            period_type=period_type,
            effective_from=SEED_DATE,
            **values,
        )
        _copy_slabs_to_version(version, period_type)
        return version

    if len(versions) == 1 and versions[0].effective_from <= SEED_DATE:
        first = versions[0]
        for key, value in values.items():
            setattr(first, key, value)
        first.save()
        _copy_slabs_to_version(first, period_type)
        return first

    current = settings_as_of(effective_from, period_type)
    current_slabs = retail_slabs_as_of(effective_from, period_type)
    if not _config_changed(current, values) and not _slabs_changed(current_slabs, slab_rows):
        latest = (
            IncentiveSettingsVersion.objects.filter(
                effective_from=effective_from,
                period_type=period_type,
            )
            .order_by("-pk")
            .first()
        )
        if latest:
            _copy_slabs_to_version(latest, period_type)
            return latest

    version = IncentiveSettingsVersion.objects.create(
        period_type=period_type,
        effective_from=effective_from,
        **values,
    )
    _copy_slabs_to_version(version, period_type)
    return version


def record_all_period_versions(all_configs, effective_from=None):
    for period_type in PERIOD_TYPES:
        payload = all_configs[period_type]
        record_period_settings_version(
            payload["config"],
            payload["slabs"],
            effective_from,
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


def change_dates_in_range(staff_id, start, end, period_type):
    """Dates in (start, end] where salary or incentive settings change."""
    dates = set()
    for d in IncentiveSettingsVersion.objects.filter(
        period_type=period_type,
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


def period_segments(staff_id, start, end, period_type):
    """Return (seg_start, seg_end) pairs covering [start, end] with constant rates."""
    points = [start] + change_dates_in_range(staff_id, start, end, period_type)
    points.append(end + timedelta(days=1))
    segments = []
    for i in range(len(points) - 1):
        seg_start = points[i]
        seg_end = points[i + 1] - timedelta(days=1)
        if seg_start <= seg_end:
            segments.append((seg_start, seg_end))
    return segments


# Legacy helpers kept for any old imports
def save_retail_slabs(slab_rows):
    """Deprecated — use incentive_master.save_period_profiles instead."""
    RetailSaleIncentiveSlab.objects.filter(period_type=IncentivePeriodType.DAILY).delete()
    for index, row in enumerate(slab_rows):
        sale_from = Decimal(str(row.get("sale_from") or 0))
        sale_to_raw = row.get("sale_to")
        sale_to = Decimal(str(sale_to_raw)) if sale_to_raw not in (None, "") else None
        incentive_value = Decimal(str(row.get("incentive_value") or 0))
        if sale_to is not None and sale_to < sale_from:
            continue
        RetailSaleIncentiveSlab.objects.create(
            period_type=IncentivePeriodType.DAILY,
            sale_from=sale_from,
            sale_to=sale_to,
            incentive_value=incentive_value,
            sort_order=index,
        )


def record_incentive_settings_version(settings_obj, effective_from=None):
    """Deprecated — kept for backward compatibility."""
    del settings_obj
    IncentivePeriodProfile.ensure_all()
    profile = IncentivePeriodProfile.get_for(IncentivePeriodType.DAILY)
    config = {
        "period_type": IncentivePeriodType.DAILY,
        **_config_dict(profile),
    }
    slabs = list(RetailSaleIncentiveSlab.objects.filter(period_type=IncentivePeriodType.DAILY))
    slab_rows = [
        {
            "sale_from": slab.sale_from,
            "sale_to": slab.sale_to,
            "incentive_value": slab.incentive_value,
        }
        for slab in slabs
    ]
    return record_period_settings_version(config, slab_rows, effective_from)
