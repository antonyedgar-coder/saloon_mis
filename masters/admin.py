from django.contrib import admin

from .models import (
    ExpenseParticular,
    IncentiveSettings,
    IncentiveSettingsVersion,
    InventoryCategory,
    Product,
    Staff,
    StaffSalaryVersion,
    Supplier,
)

admin.site.register(Supplier)
admin.site.register(Staff)
admin.site.register(StaffSalaryVersion)
admin.site.register(IncentiveSettings)
admin.site.register(IncentiveSettingsVersion)
admin.site.register(InventoryCategory)
admin.site.register(Product)
admin.site.register(ExpenseParticular)
