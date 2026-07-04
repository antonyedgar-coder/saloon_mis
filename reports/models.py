from django.conf import settings
from django.db import models

from core.models import Branch
from masters.models import ExpenseParticular, Staff


class DailySalesReport(models.Model):
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name="dsr")
    report_date = models.DateField()

    # Income
    net_service_income = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    membership_card = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    ear_piercing = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    other_income = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    product_sale_18 = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    product_sale_5 = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    gst = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    bridal_advance = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # Walk-ins
    male_walkins = models.PositiveIntegerField(default=0)
    male_income = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    female_walkins = models.PositiveIntegerField(default=0)
    female_income = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    kids_walkins = models.PositiveIntegerField(default=0)
    kids_income = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # Mode of payment
    card_payment = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    upi_payment = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    cash_payment = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # Marketing updates
    calls_done = models.PositiveIntegerField(default=0)
    zooty_appointment = models.PositiveIntegerField(default=0)
    google_appointment = models.PositiveIntegerField(default=0)
    just_dial = models.PositiveIntegerField(default=0)
    status_story = models.CharField(max_length=200, blank=True)
    broadcast = models.PositiveIntegerField(default=0)
    google_reviews_request = models.CharField(max_length=200, blank=True)
    new_clients = models.PositiveIntegerField(default=0)

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("branch", "report_date")]
        ordering = ["-report_date"]

    @property
    def total_walkins(self):
        return self.male_walkins + self.female_walkins + self.kids_walkins

    @property
    def total_walkin_income(self):
        return self.male_income + self.female_income + self.kids_income

    @property
    def total_income(self):
        return (
            self.net_service_income
            + self.membership_card
            + self.ear_piercing
            + self.other_income
            + self.product_sale_18
            + self.product_sale_5
            + self.gst
            + self.bridal_advance
        )


class DsrStaffLine(models.Model):
    report = models.ForeignKey(
        DailySalesReport,
        on_delete=models.CASCADE,
        related_name="staff_lines",
    )
    staff = models.ForeignKey(Staff, on_delete=models.PROTECT, related_name="dsr_lines")
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.staff.name}: {self.amount}"


class PettyCashTransaction(models.Model):
    class Type(models.TextChoices):
        OPENING = "OPENING", "Opening Balance"
        RECEIPT = "RECEIPT", "Receipt"
        PAYMENT = "PAYMENT", "Payment"

    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name="petty_cash")
    entry_date = models.DateField()
    transaction_type = models.CharField(max_length=10, choices=Type.choices)
    particulars = models.CharField(
        max_length=500,
        blank=True,
        help_text="Free text for cash received (receipts) or opening balance notes",
    )
    expense_particular = models.ForeignKey(
        ExpenseParticular,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="petty_cash_payments",
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["entry_date", "created_at"]

    @property
    def display_particulars(self):
        if self.transaction_type == self.Type.OPENING:
            return self.particulars or "Opening balance"
        if self.transaction_type == self.Type.RECEIPT:
            return self.particulars
        if self.expense_particular:
            return self.expense_particular.name
        return self.particulars or "—"
