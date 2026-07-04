from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Sum

from core.models import Branch, DocumentSequence, User
from masters.models import Product, Supplier


class GrnStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    POSTED = "POSTED", "Posted"


class Grn(models.Model):
    Status = GrnStatus

    grn_number = models.CharField(max_length=50, unique=True)
    date = models.DateField()
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name="grns")
    supplier_invoice = models.CharField(max_length=100, blank=True)
    remarks = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=GrnStatus.choices, default=GrnStatus.DRAFT)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date"]

    def __str__(self):
        return self.grn_number


class GrnLine(models.Model):
    grn = models.ForeignKey(Grn, on_delete=models.CASCADE, related_name="lines")
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=12, decimal_places=2)
    rate = models.DecimalField(max_digits=12, decimal_places=2)
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    def save(self, *args, **kwargs):
        self.amount = self.quantity * self.rate
        super().save(*args, **kwargs)


class OutwardRegisterStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    DISPATCHED = "DISPATCHED", "Dispatched"


class OutwardRegister(models.Model):
    Status = OutwardRegisterStatus

    register_number = models.CharField(max_length=50, unique=True)
    date = models.DateField()
    remarks = models.TextField(blank=True)
    status = models.CharField(
        max_length=12,
        choices=OutwardRegisterStatus.choices,
        default=OutwardRegisterStatus.DRAFT,
    )
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date"]


class OutwardInvoiceStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    DISPATCHED = "DISPATCHED", "Dispatched"
    RECEIVED = "RECEIVED", "Received"
    PARTIALLY_RECEIVED = "PARTIALLY_RECEIVED", "Partially Received"


class OutwardInvoice(models.Model):
    Status = OutwardInvoiceStatus

    invoice_number = models.CharField(max_length=50, unique=True)
    register = models.ForeignKey(
        OutwardRegister, on_delete=models.CASCADE, related_name="invoices"
    )
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name="inward_invoices")
    status = models.CharField(
        max_length=20,
        choices=OutwardInvoiceStatus.choices,
        default=OutwardInvoiceStatus.DRAFT,
    )
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class OutwardInvoiceLine(models.Model):
    invoice = models.ForeignKey(
        OutwardInvoice, on_delete=models.CASCADE, related_name="lines"
    )
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity_sent = models.DecimalField(max_digits=12, decimal_places=2)
    quantity_received = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    expiry_date = models.DateField(
        null=True,
        blank=True,
        help_text="Must be set at the branch before stock can be accepted.",
    )


class TransferAcceptance(models.Model):
    invoice = models.ForeignKey(
        OutwardInvoice, on_delete=models.CASCADE, related_name="acceptances"
    )
    accepted_at = models.DateTimeField(auto_now_add=True)
    remarks = models.TextField(blank=True)
    shortage_remarks = models.TextField(blank=True)


class BranchOutwardType(models.TextChoices):
    RETAIL_SALE = "RETAIL_SALE", "Retail Sale"
    CONSUMPTION = "CONSUMPTION", "Consumption"


class BranchOutward(models.Model):
    Type = BranchOutwardType

    doc_number = models.CharField(max_length=50, unique=True)
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name="outwards")
    date = models.DateTimeField()
    type = models.CharField(max_length=20, choices=BranchOutwardType.choices)
    remarks = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date"]


class BranchOutwardLine(models.Model):
    branch_outward = models.ForeignKey(
        BranchOutward, on_delete=models.CASCADE, related_name="lines"
    )
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=12, decimal_places=2)
    rate = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    staff = models.ForeignKey(
        "masters.Staff",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="retail_sales",
    )

    def save(self, *args, **kwargs):
        if self.amount == 0 and self.rate:
            self.amount = self.quantity * self.rate
        super().save(*args, **kwargs)


class StockRefType(models.TextChoices):
    GRN = "GRN", "GRN"
    OUTWARD_DISPATCH = "OUTWARD_DISPATCH", "Outward Dispatch"
    TRANSFER_RECEIVE = "TRANSFER_RECEIVE", "Transfer Receive"
    BRANCH_OUTWARD = "BRANCH_OUTWARD", "Branch Outward"


class StockLedger(models.Model):
    RefType = StockRefType

    branch = models.ForeignKey(
        Branch, null=True, blank=True, on_delete=models.PROTECT, related_name="stock_ledger"
    )
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="stock_ledger")
    qty_delta = models.DecimalField(max_digits=12, decimal_places=2)
    ref_type = models.CharField(max_length=20, choices=StockRefType.choices)
    ref_id = models.CharField(max_length=50)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["branch", "product"]),
            models.Index(fields=["ref_type", "ref_id"]),
        ]

    @classmethod
    def balance(cls, branch_id, product_id) -> Decimal:
        result = cls.objects.filter(branch_id=branch_id, product_id=product_id).aggregate(
            total=Sum("qty_delta")
        )
        return result["total"] or Decimal("0")

    @classmethod
    def add_entries(cls, entries, user):
        cls.objects.bulk_create(
            [
                cls(
                    branch_id=e.get("branch_id"),
                    product_id=e["product_id"],
                    qty_delta=e["qty_delta"],
                    ref_type=e["ref_type"],
                    ref_id=str(e["ref_id"]),
                    created_by=user,
                )
                for e in entries
            ]
        )

    @classmethod
    def assert_sufficient(cls, branch_id, lines, allow_override=False):
        if allow_override:
            return
        for line in lines:
            bal = cls.balance(branch_id, line["product_id"])
            if bal < line["quantity"]:
                product = Product.objects.get(pk=line["product_id"])
                raise ValueError(
                    f"Insufficient stock for {product.name}. Available: {bal}, required: {line['quantity']}"
                )

    @classmethod
    def assert_central_sufficient(cls, lines):
        for line in lines:
            bal = cls.balance(None, line["product_id"])
            if bal < line["quantity"]:
                product = Product.objects.get(pk=line["product_id"])
                raise ValueError(
                    f"Insufficient central stock for {product.name}. Available: {bal}"
                )
