from decimal import Decimal

INCOME_FIELD_NAMES = (
    "net_service_income",
    "membership_card",
    "ear_piercing",
    "other_income",
    "product_sale_18",
    "product_sale_5",
    "gst",
    "bridal_advance",
)

PAYMENT_FIELD_NAMES = (
    "card_payment",
    "upi_payment",
    "cash_payment",
)


def income_total(data):
    return sum(data.get(name, Decimal("0")) for name in INCOME_FIELD_NAMES)


def walkin_income_total(data):
    return (
        data.get("male_income", Decimal("0"))
        + data.get("female_income", Decimal("0"))
        + data.get("kids_income", Decimal("0"))
    )


def payment_total(data):
    return sum(data.get(name, Decimal("0")) for name in PAYMENT_FIELD_NAMES)


def staff_performance_total(staff_amounts):
    return sum(staff_amounts, Decimal("0"))


def validate_dsr_totals(data, staff_amounts):
    errors = []
    net_service = data.get("net_service_income", Decimal("0"))
    walkin_total = walkin_income_total(data)
    staff_total = staff_performance_total(staff_amounts)
    income_sum = income_total(data)
    payment_sum = payment_total(data)

    if walkin_total > net_service:
        errors.append(
            f"Walk Ins income total (₹{walkin_total}) cannot be greater than Net Service income (₹{net_service})."
        )
    if staff_total > net_service:
        errors.append(
            f"Staff Performance total (₹{staff_total}) cannot be greater than Net Service income (₹{net_service})."
        )
    if income_sum > payment_sum:
        errors.append(
            f"Total Income (₹{income_sum}) cannot be greater than Mode of Payment total (₹{payment_sum})."
        )
    return errors
