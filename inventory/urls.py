from django.urls import path

from . import views

app_name = "inventory"

urlpatterns = [
    path("", views.InventoryHubView.as_view(), name="hub"),
    path("grn/", views.GrnCreateView.as_view(), name="grn"),
    path("outward/", views.OutwardCreateView.as_view(), name="outward"),
    path("receive/", views.ReceiveStockView.as_view(), name="receive"),
    path("branch-outward/", views.BranchOutwardView.as_view(), name="branch_outward"),
    path("stock/", views.StockBalanceView.as_view(), name="stock"),
]
