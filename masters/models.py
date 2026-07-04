from django.db import models


class ProductType(models.TextChoices):
    RETAIL = "RETAIL", "Retail"
    CONSUMPTION = "CONSUMPTION", "Consumption"
    BOTH = "BOTH", "Both"


class Supplier(models.Model):
    name = models.CharField(max_length=200)
    gstin = models.CharField(max_length=20, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class ExpenseParticular(models.Model):
    name = models.CharField(max_length=200, unique=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Staff(models.Model):
    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20, blank=True)
    designation = models.CharField(max_length=100, blank=True)
    salary = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Monthly salary — used for incentive calculations.",
    )
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "staff"

    def __str__(self):
        return self.name


class StaffSalaryVersion(models.Model):
    """Salary effective from a date — past incentives keep the old salary."""

    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name="salary_versions")
    salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    effective_from = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-effective_from", "-pk"]
        indexes = [models.Index(fields=["staff", "effective_from"])]

    def __str__(self):
        return f"{self.staff.name}: {self.salary} from {self.effective_from}"


class IncentiveSettings(models.Model):
    """Singleton incentive rules used for target and incentive calculations."""

    incentive_percent = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0,
        help_text="Incentive percentage applied on target achieved when target is met.",
    )
    salary_times = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=5,
        help_text="Number of times of salary used as the monthly target.",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "incentive settings"
        verbose_name_plural = "incentive settings"

    def __str__(self):
        return "Incentive settings"

    @classmethod
    def get_solo(cls):
        obj = cls.objects.first()
        if obj is None:
            obj = cls.objects.create()
        return obj


class IncentiveSettingsVersion(models.Model):
    """Incentive rules effective from a date — past periods keep old rules."""

    incentive_percent = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    salary_times = models.DecimalField(max_digits=6, decimal_places=2, default=5)
    effective_from = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-effective_from", "-pk"]
        indexes = [models.Index(fields=["effective_from"])]

    def __str__(self):
        return f"{self.incentive_percent}% / {self.salary_times}x from {self.effective_from}"


class InventoryCategory(models.Model):
    name = models.CharField(max_length=200, unique=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "inventory categories"

    def __str__(self):
        return self.name


class Product(models.Model):
    sku = models.CharField(max_length=50, unique=True, blank=True)
    name = models.CharField(max_length=200)
    inventory_category = models.ForeignKey(
        InventoryCategory,
        on_delete=models.PROTECT,
        related_name="products",
    )
    unit = models.CharField(max_length=20, default="pcs")
    product_type = models.CharField(
        max_length=20, choices=ProductType.choices, default=ProductType.BOTH
    )
    purchase_rate = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    selling_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    reorder_level = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new and not self.sku:
            self.sku = f"INV-{self.pk:05d}"
            Product.objects.filter(pk=self.pk).update(sku=self.sku)
