from django.urls import path
from django.views.generic import RedirectView

from . import views

app_name = "reports"

urlpatterns = [
    path("dsr/", views.DsrView.as_view(), name="dsr"),
    path("dsr/load/", views.DsrLoadView.as_view(), name="dsr_load"),
    path("petty-cash/", views.PettyCashView.as_view(), name="petty_cash"),
    path(
        "petty-cash/receipt/",
        RedirectView.as_view(url="/reports/petty-cash/?type=receipt", permanent=False),
        name="petty_cash_receipt",
    ),
    path(
        "petty-cash/payment/",
        RedirectView.as_view(url="/reports/petty-cash/?type=payment", permanent=False),
        name="petty_cash_payment",
    ),
    path("sales/", views.SalesReportView.as_view(), name="sales"),
    path(
        "staff-performance/",
        views.StaffPerformanceReportView.as_view(),
        name="staff_performance",
    ),
    path(
        "incentive/",
        views.IncentiveReportView.as_view(),
        name="incentive",
    ),
    path("inventory/", views.InventoryReportView.as_view(), name="inventory"),
    path("", views.ReportsHubView.as_view(), name="index"),
]
