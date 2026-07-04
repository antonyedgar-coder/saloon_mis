from django.urls import path

from . import views

app_name = "masters"

urlpatterns = [
    path("branches/", views.BranchListView.as_view(), name="branches"),
    path("inventory-categories/", views.InventoryCategoryListView.as_view(), name="inventory_categories"),
    path("products/", views.ProductListView.as_view(), name="products"),
    path("suppliers/", views.SupplierListView.as_view(), name="suppliers"),
    path("staff/", views.StaffListView.as_view(), name="staff"),
    path("incentive/", views.IncentiveSettingsView.as_view(), name="incentive"),
    path("users/", views.UserListView.as_view(), name="users"),
    path("expenses/", views.ExpenseParticularListView.as_view(), name="expenses"),
]
