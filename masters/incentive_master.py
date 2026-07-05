from decimal import Decimal, InvalidOperation

from masters.models import (
    IncentivePeriodProfile,
    IncentivePeriodType,
    RetailSaleIncentiveSlab,
)

PERIOD_TYPES = tuple(IncentivePeriodType.values)
PERIOD_LABELS = dict(IncentivePeriodType.choices)


def _decimal(value, default="0"):
    try:
        return Decimal(str(value if value not in (None, "") else default))
    except InvalidOperation:
        return Decimal(default)


def _profile_dict(profile):
    return {
        "service_enabled": profile.service_enabled,
        "incentive_percent": profile.incentive_percent,
        "salary_times": profile.salary_times,
        "retail_enabled": profile.retail_enabled,
        "staff_performance_enabled": profile.staff_performance_enabled,
        "makeup_percent": profile.makeup_percent,
        "google_review_with_photo_incentive": profile.google_review_with_photo_incentive,
        "google_review_without_photo_incentive": profile.google_review_without_photo_incentive,
        "ear_piercing_incentive": profile.ear_piercing_incentive,
        "watts_incentive": profile.watts_incentive,
        "membership_card_incentive": profile.membership_card_incentive,
        "ot_incentive": profile.ot_incentive,
    }


def profiles_for_template():
    IncentivePeriodProfile.ensure_all()
    profiles = {}
    slabs = {}
    for period_type in PERIOD_TYPES:
        profile = IncentivePeriodProfile.get_for(period_type)
        profiles[period_type] = _profile_dict(profile)
        profiles[period_type]["period_label"] = PERIOD_LABELS[period_type]
        slabs[period_type] = list(
            RetailSaleIncentiveSlab.objects.filter(period_type=period_type)
        )
    return profiles, slabs


def parse_period_config(post, period_type):
    prefix = f"{period_type}_"
    return {
        "period_type": period_type,
        "service_enabled": post.get(f"{prefix}service_enabled") == "on",
        "incentive_percent": _decimal(post.get(f"{prefix}incentive_percent")),
        "salary_times": _decimal(post.get(f"{prefix}salary_times")),
        "retail_enabled": post.get(f"{prefix}retail_enabled") == "on",
        "staff_performance_enabled": post.get(f"{prefix}staff_performance_enabled") == "on",
        "makeup_percent": _decimal(post.get(f"{prefix}makeup_percent")),
        "google_review_with_photo_incentive": _decimal(
            post.get(f"{prefix}google_review_with_photo_incentive")
        ),
        "google_review_without_photo_incentive": _decimal(
            post.get(f"{prefix}google_review_without_photo_incentive")
        ),
        "ear_piercing_incentive": _decimal(post.get(f"{prefix}ear_piercing_incentive")),
        "watts_incentive": _decimal(post.get(f"{prefix}watts_incentive")),
        "membership_card_incentive": _decimal(post.get(f"{prefix}membership_card_incentive")),
        "ot_incentive": _decimal(post.get(f"{prefix}ot_incentive")),
    }


def parse_slab_rows(post, period_type):
    prefix = f"{period_type}_"
    sale_from_list = post.getlist(f"{prefix}slab_sale_from")
    sale_to_list = post.getlist(f"{prefix}slab_sale_to")
    incentive_list = post.getlist(f"{prefix}slab_incentive_value")
    rows = []
    for index, sale_from in enumerate(sale_from_list):
        sale_to = sale_to_list[index] if index < len(sale_to_list) else ""
        incentive_value = incentive_list[index] if index < len(incentive_list) else ""
        if not str(sale_from).strip() and not str(incentive_value).strip():
            continue
        rows.append(
            {
                "sale_from": sale_from,
                "sale_to": sale_to,
                "incentive_value": incentive_value,
            }
        )
    return rows


def parse_all_period_configs(post):
    return {
        period_type: {
            "config": parse_period_config(post, period_type),
            "slabs": parse_slab_rows(post, period_type),
        }
        for period_type in PERIOD_TYPES
    }


def save_period_profiles(all_configs):
    for period_type, payload in all_configs.items():
        config = payload["config"]
        profile = IncentivePeriodProfile.get_for(period_type)
        for key, value in config.items():
            if key != "period_type":
                setattr(profile, key, value)
        profile.save()

        RetailSaleIncentiveSlab.objects.filter(period_type=period_type).delete()
        for index, row in enumerate(payload["slabs"]):
            sale_from = _decimal(row.get("sale_from"))
            sale_to_raw = row.get("sale_to")
            sale_to = _decimal(sale_to_raw) if str(sale_to_raw).strip() else None
            incentive_value = _decimal(row.get("incentive_value"))
            if sale_to is not None and sale_to < sale_from:
                continue
            RetailSaleIncentiveSlab.objects.create(
                period_type=period_type,
                sale_from=sale_from,
                sale_to=sale_to,
                incentive_value=incentive_value,
                sort_order=index,
            )
