from django.contrib import admin

from .models import (
    ExpenseParticular,
    IncentivePeriodProfile,
    IncentiveSettings,
    IncentiveSettingsVersion,
    InventoryCategory,
    Product,
    RetailSaleIncentiveSlab,
    RetailSaleIncentiveSlabVersion,
    Staff,
    StaffSalaryVersion,
    Supplier,
)

admin.site.register(Supplier)
admin.site.register(Staff)
admin.site.register(StaffSalaryVersion)
admin.site.register(IncentiveSettings)
admin.site.register(IncentivePeriodProfile)
admin.site.register(IncentiveSettingsVersion)
admin.site.register(RetailSaleIncentiveSlab)
admin.site.register(RetailSaleIncentiveSlabVersion)
admin.site.register(InventoryCategory)
admin.site.register(Product)
admin.site.register(ExpenseParticular)
