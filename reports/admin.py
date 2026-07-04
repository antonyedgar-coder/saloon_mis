from django.contrib import admin

from .models import DailySalesReport, DsrStaffLine, PettyCashTransaction


class DsrStaffLineInline(admin.TabularInline):
    model = DsrStaffLine
    extra = 0


@admin.register(DailySalesReport)
class DailySalesReportAdmin(admin.ModelAdmin):
    inlines = [DsrStaffLineInline]
    list_display = ("report_date", "branch", "total_income", "total_walkins")


admin.site.register(PettyCashTransaction)
