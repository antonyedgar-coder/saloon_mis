from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View

from core.mixins import LoginRequiredMixin
from core.models import Branch, DocumentSequence, Role
from masters.models import Product, Staff, Supplier

from .export_utils import (
    build_filter_urls,
    csv_response,
    dated_filename,
    filter_queryset_by_date,
    filter_queryset_by_datetime_date,
)
from .permissions import (
    InvBranchOutwardRequiredMixin,
    InvGrnRequiredMixin,
    InvOutwardRequiredMixin,
    InvReceiveRequiredMixin,
    InvStockRequiredMixin,
)

from .models import (
    BranchOutward,
    BranchOutwardLine,
    BranchOutwardType,
    Grn,
    GrnLine,
    OutwardInvoice,
    OutwardInvoiceStatus,
    OutwardRegister,
    StockLedger,
    StockRefType,
)
from .services import accept_transfer_line, delete_grn, dispatch_outward, post_grn, update_grn


def _master_list(queryset):
    return [{"id": obj.pk, "name": obj.name} for obj in queryset]


def _parse_product_lines(request):
    product_ids = request.POST.getlist("product_id")
    quantities = request.POST.getlist("quantity")
    lines = []
    for pid, qty in zip(product_ids, quantities):
        pid = (pid or "").strip()
        qty_text = (qty or "").strip()
        if not pid or not qty_text:
            continue
        try:
            quantity = Decimal(qty_text)
        except InvalidOperation:
            continue
        if quantity <= 0:
            continue
        lines.append({"product_id": int(pid), "quantity": quantity})
    return lines


def _product_rate(product):
    if product.purchase_rate is not None:
        return product.purchase_rate
    return Decimal("0")


def _parse_branch_outward_lines(request, is_retail):
    product_ids = request.POST.getlist("product_id")
    quantities = request.POST.getlist("quantity")
    amounts = request.POST.getlist("line_amount") if is_retail else []
    staff_ids = request.POST.getlist("staff_id") if is_retail else []
    lines = []
    for index, (pid, qty) in enumerate(zip(product_ids, quantities)):
        pid = (pid or "").strip()
        qty_text = (qty or "").strip()
        if not pid or not qty_text:
            continue
        try:
            quantity = Decimal(qty_text)
        except InvalidOperation:
            continue
        if quantity <= 0:
            continue
        line = {"product_id": int(pid), "quantity": quantity}
        if is_retail:
            amount_text = (amounts[index] if index < len(amounts) else "").strip()
            staff_id = (staff_ids[index] if index < len(staff_ids) else "").strip()
            if not amount_text or not staff_id:
                continue
            try:
                amount = Decimal(amount_text)
            except InvalidOperation:
                continue
            if amount <= 0:
                continue
            line["amount"] = amount
            line["rate"] = amount / quantity
            line["staff_id"] = int(staff_id)
        else:
            line["amount"] = Decimal("0")
            line["rate"] = Decimal("0")
            line["staff_id"] = None
        lines.append(line)
    return lines


class GrnCreateView(InvGrnRequiredMixin, View):
    template_name = "inventory/grn_list.html"

    def get_context(self, request, edit_grn=None):
        products = Product.objects.filter(active=True)
        suppliers = Supplier.objects.filter(active=True)
        edit_lines = []
        if edit_grn:
            edit_lines = [
                {
                    "product_id": line.product_id,
                    "product_name": line.product.name,
                    "quantity": str(line.quantity),
                }
                for line in edit_grn.lines.all()
            ]
        filters = build_filter_urls(request, request.path)
        grns = Grn.objects.select_related("supplier", "created_by").prefetch_related(
            "lines__product"
        )
        grns = filter_queryset_by_date(
            grns, "date", filters["parsed_from_date"], filters["parsed_to_date"]
        )
        return {
            "grns": grns,
            "suppliers_list": _master_list(suppliers),
            "products_list": _master_list(products),
            "today": timezone.localdate().isoformat(),
            "edit_grn": edit_grn,
            "edit_lines": edit_lines,
            **filters,
        }

    def get(self, request):
        edit_id = request.GET.get("edit")
        edit_grn = None
        if edit_id:
            edit_grn = (
                Grn.objects.select_related("supplier")
                .prefetch_related("lines__product")
                .filter(pk=edit_id)
                .first()
            )
        ctx = self.get_context(request, edit_grn)
        if ctx["export_csv"]:
            rows = []
            for g in ctx["grns"]:
                for line in g.lines.all():
                    rows.append(
                        [
                            g.grn_number,
                            g.date,
                            g.supplier.name,
                            g.supplier_invoice,
                            line.product.name,
                            line.quantity,
                        ]
                    )
            return csv_response(
                dated_filename("grn"),
                ["GRN", "Date", "Supplier", "Invoice No", "Product", "Quantity"],
                rows,
            )
        return render(request, self.template_name, ctx)

    def post(self, request):
        action = request.POST.get("action")

        if action == "delete":
            grn = get_object_or_404(Grn, pk=request.POST.get("grn_id"))
            try:
                delete_grn(grn, request.user)
                messages.success(request, f"GRN {grn.grn_number} deleted.")
            except ValueError as e:
                messages.error(request, str(e))
            return redirect("inventory:grn")

        supplier_id = request.POST.get("supplier_id")
        if not supplier_id:
            messages.error(request, "Select a supplier from the list.")
            return redirect("inventory:grn")

        edit_id = request.POST.get("edit_id")
        lines = _parse_product_lines(request)
        if not lines:
            messages.error(
                request,
                "Add at least one product line — select a product from the dropdown and enter quantity.",
            )
            if edit_id:
                return redirect(f"{request.path}?edit={edit_id}")
            return redirect("inventory:grn")

        if edit_id:
            grn = get_object_or_404(Grn, pk=edit_id)
            try:
                update_grn(
                    grn,
                    request.user,
                    date=request.POST.get("date"),
                    supplier_id=int(supplier_id),
                    supplier_invoice=request.POST.get("supplier_invoice", ""),
                    lines=lines,
                )
                messages.success(request, f"GRN {grn.grn_number} updated.")
            except ValueError as e:
                messages.error(request, str(e))
                return redirect(f"{request.path}?edit={edit_id}")
            return redirect("inventory:grn")

        grn = Grn.objects.create(
            grn_number=DocumentSequence.next_number("GRN"),
            date=request.POST.get("date"),
            supplier_id=supplier_id,
            supplier_invoice=request.POST.get("supplier_invoice", ""),
            remarks=request.POST.get("remarks", ""),
            created_by=request.user,
        )
        try:
            for line in lines:
                product = Product.objects.get(pk=line["product_id"])
                GrnLine.objects.create(
                    grn=grn,
                    product_id=line["product_id"],
                    quantity=line["quantity"],
                    rate=_product_rate(product),
                )
            post_grn(grn, request.user)
        except (ValidationError, ValueError) as e:
            grn.delete()
            messages.error(request, str(e))
            return redirect("inventory:grn")

        messages.success(request, f"GRN {grn.grn_number} saved. Central stock updated.")
        return redirect("inventory:grn")


class OutwardCreateView(InvOutwardRequiredMixin, View):
    template_name = "inventory/outward_list.html"

    def get(self, request):
        products = Product.objects.filter(active=True)
        filters = build_filter_urls(request, request.path)
        registers = OutwardRegister.objects.prefetch_related(
            "invoices__branch", "invoices__lines__product"
        )
        registers = filter_queryset_by_date(
            registers, "date", filters["parsed_from_date"], filters["parsed_to_date"]
        )
        if filters["export_csv"]:
            rows = []
            for r in registers:
                for inv in r.invoices.all():
                    for line in inv.lines.all():
                        rows.append(
                            [
                                r.register_number,
                                r.date,
                                inv.branch.name,
                                inv.invoice_number,
                                line.product.name,
                                line.quantity_sent,
                            ]
                        )
            return csv_response(
                dated_filename("outward_register"),
                ["Register", "Date", "Branch", "Invoice", "Product", "Qty Sent"],
                rows,
            )
        return render(
            request,
            self.template_name,
            {
                "registers": registers,
                "branches": Branch.objects.filter(active=True),
                "products_list": _master_list(products),
                "today": timezone.localdate().isoformat(),
                **filters,
            },
        )

    def post(self, request):
        branch_id = request.POST.get("branch_id")
        lines = []
        for line in _parse_product_lines(request):
            lines.append({"product_id": line["product_id"], "quantity_sent": line["quantity"]})

        if not branch_id or not lines:
            messages.error(request, "Branch and at least one product line are required.")
            return redirect("inventory:outward")

        register = OutwardRegister.objects.create(
            register_number=DocumentSequence.next_number("OR"),
            date=request.POST.get("date"),
            remarks=request.POST.get("remarks", ""),
            created_by=request.user,
        )
        try:
            dispatch_outward(
                register,
                [{"branch_id": int(branch_id), "lines": lines}],
                request.user,
            )
            messages.success(request, f"Dispatched to branch — register {register.register_number}.")
        except ValueError as e:
            register.delete()
            messages.error(request, str(e))
        return redirect("inventory:outward")


class ReceiveStockView(InvReceiveRequiredMixin, View):
    template_name = "inventory/receive_list.html"

    def get_queryset(self, user, from_date=None, to_date=None):
        qs = OutwardInvoice.objects.select_related(
            "branch", "register"
        ).prefetch_related("lines__product")
        if not user.is_central():
            qs = qs.filter(branch_id__in=user.branch_ids())
        qs = filter_queryset_by_date(qs, "register__date", from_date, to_date)
        return qs.order_by("-register__date")

    def get_pending_queryset(self, user):
        return self.get_queryset(user).filter(
            status__in=[
                OutwardInvoice.Status.DISPATCHED,
                OutwardInvoice.Status.PARTIALLY_RECEIVED,
            ]
        )

    def get(self, request):
        filters = build_filter_urls(request, request.path)
        invoices = self.get_queryset(
            request.user, filters["parsed_from_date"], filters["parsed_to_date"]
        )
        if filters["export_csv"]:
            rows = []
            for inv in invoices:
                for line in inv.lines.all():
                    rows.append(
                        [
                            inv.invoice_number,
                            inv.register.date,
                            inv.branch.name,
                            inv.get_status_display(),
                            line.product.name,
                            line.quantity_sent,
                            line.quantity_received,
                            line.expiry_date or "",
                        ]
                    )
            return csv_response(
                dated_filename("receive_stock"),
                [
                    "Dispatch",
                    "Date",
                    "Branch",
                    "Status",
                    "Product",
                    "Qty Sent",
                    "Qty Received",
                    "Expiry Date",
                ],
                rows,
            )
        invoice = None
        invoice_id = request.GET.get("invoice")
        if invoice_id:
            invoice = get_object_or_404(invoices, pk=invoice_id)
        return render(
            request,
            self.template_name,
            {
                "invoices": invoices,
                "pending_invoices": self.get_pending_queryset(request.user),
                "selected": invoice,
                **filters,
            },
        )

    def post(self, request):
        invoice = get_object_or_404(
            self.get_pending_queryset(request.user), pk=request.POST.get("invoice_id")
        )
        line = get_object_or_404(invoice.lines.all(), pk=request.POST.get("line_id"))
        action = request.POST.get("action", "accept")
        expiry_raw = (request.POST.get("expiry_date") or "").strip()
        redirect_url = f"{request.path}?invoice={invoice.pk}"
        for key in ("from_date", "to_date"):
            if request.GET.get(key):
                redirect_url += f"&{key}={request.GET.get(key)}"

        if action == "save_expiry":
            if not expiry_raw:
                messages.error(request, f"Enter expiry date for {line.product.name}.")
                return redirect(redirect_url)
            line.expiry_date = expiry_raw
            line.save(update_fields=["expiry_date"])
            messages.success(
                request, f"Expiry date saved for {line.product.name}."
            )
            return redirect(redirect_url)

        qty = request.POST.get("quantity_received") or line.quantity_sent
        try:
            accept_transfer_line(
                invoice,
                line,
                qty,
                request.user,
                expiry_date=expiry_raw or None,
            )
            messages.success(
                request,
                f"Accepted {line.product.name} into {invoice.branch.name} stock.",
            )
        except ValueError as e:
            messages.error(request, str(e))
        return redirect(redirect_url)


class BranchOutwardView(InvBranchOutwardRequiredMixin, View):
    template_name = "inventory/branch_outward_list.html"

    def get_outwards(self, user, from_date=None, to_date=None):
        qs = BranchOutward.objects.select_related("branch").prefetch_related(
            "lines__product", "lines__staff"
        )
        if not user.is_central():
            qs = qs.filter(branch_id__in=user.branch_ids())
        qs = filter_queryset_by_datetime_date(qs, "date", from_date, to_date)
        return qs.order_by("-date")

    def get_branches(self, user):
        if user.is_central():
            return Branch.objects.filter(active=True)
        return user.branches.filter(active=True)

    def get(self, request):
        products = Product.objects.filter(active=True)
        filters = build_filter_urls(request, request.path)
        outwards = self.get_outwards(
            request.user, filters["parsed_from_date"], filters["parsed_to_date"]
        )
        if filters["export_csv"]:
            rows = []
            for o in outwards:
                for line in o.lines.all():
                    rows.append(
                        [
                            o.doc_number,
                            timezone.localtime(o.date).date(),
                            o.branch.name,
                            o.get_type_display(),
                            line.product.name,
                            line.quantity,
                            line.amount if o.type == BranchOutwardType.RETAIL_SALE else "",
                            line.staff.name if line.staff else "",
                        ]
                    )
            return csv_response(
                dated_filename("branch_outward"),
                [
                    "Document",
                    "Date",
                    "Branch",
                    "Type",
                    "Product",
                    "Quantity",
                    "Amount",
                    "Staff",
                ],
                rows,
            )
        staff = Staff.objects.filter(active=True)
        return render(
            request,
            self.template_name,
            {
                "outwards": outwards,
                "branches": self.get_branches(request.user),
                "products_list": _master_list(products),
                "staff_list": _master_list(staff),
                **filters,
            },
        )

    def post(self, request):
        branch_id = int(request.POST.get("branch_id"))
        if not request.user.can_access_branch(branch_id):
            messages.error(request, "Access denied for this branch.")
            return redirect("inventory:branch_outward")

        outward_type = request.POST.get("type")
        is_retail = outward_type == BranchOutwardType.RETAIL_SALE
        lines = _parse_branch_outward_lines(request, is_retail)

        if not lines:
            if is_retail:
                messages.error(
                    request,
                    "Add at least one line with product, quantity, amount, and staff.",
                )
            else:
                messages.error(request, "Add at least one product line.")
            return redirect("inventory:branch_outward")

        stock_lines = [{"product_id": l["product_id"], "quantity": l["quantity"]} for l in lines]
        allow_override = request.user.role in (Role.SUPER_ADMIN, Role.BRANCH_MANAGER)
        try:
            StockLedger.assert_sufficient(branch_id, stock_lines, allow_override)
        except ValueError as e:
            messages.error(request, str(e))
            return redirect("inventory:branch_outward")

        prefix = "RS" if is_retail else "CN"
        outward = BranchOutward.objects.create(
            doc_number=DocumentSequence.next_number(prefix),
            branch_id=branch_id,
            date=timezone.now(),
            type=outward_type,
            remarks=request.POST.get("remarks", ""),
            created_by=request.user,
        )
        ledger = []
        for line in lines:
            BranchOutwardLine.objects.create(
                branch_outward=outward,
                product_id=line["product_id"],
                quantity=line["quantity"],
                rate=line["rate"],
                amount=line["amount"],
                staff_id=line["staff_id"],
            )
            ledger.append(
                {
                    "branch_id": branch_id,
                    "product_id": line["product_id"],
                    "qty_delta": -line["quantity"],
                    "ref_type": StockRefType.BRANCH_OUTWARD,
                    "ref_id": outward.pk,
                }
            )
        StockLedger.add_entries(ledger, request.user)
        messages.success(request, f"Saved {outward.doc_number}. Branch stock reduced.")
        return redirect("inventory:branch_outward")


class StockBalanceView(InvStockRequiredMixin, View):
    template_name = "inventory/stock_balance.html"

    def get(self, request):
        branch_id = request.GET.get("branch")
        if branch_id == "central":
            branch_id = None
        elif branch_id:
            branch_id = int(branch_id)
            if not request.user.can_access_branch(branch_id):
                messages.error(request, "Access denied.")
                return redirect("inventory:stock")
        elif request.user.branch_ids() and not request.user.is_central():
            branch_id = request.user.branch_ids()[0]
        else:
            branch_id = None

        stock = [
            {"product": p, "quantity": StockLedger.balance(branch_id, p.pk)}
            for p in Product.objects.filter(active=True).select_related("inventory_category")
        ]
        branches = (
            Branch.objects.filter(active=True)
            if request.user.is_central()
            else request.user.branches.all()
        )
        filters = build_filter_urls(request, request.path)
        if filters["export_csv"]:
            location = "Central" if branch_id is None else Branch.objects.get(pk=branch_id).name
            rows = [
                [location, s["product"].name, s["product"].inventory_category.name, s["quantity"], s["product"].unit]
                for s in stock
            ]
            return csv_response(
                dated_filename("stock_balance"),
                ["Location", "Product", "Category", "Quantity", "Unit"],
                rows,
            )
        return render(
            request,
            self.template_name,
            {"stock": stock, "branches": branches, "selected_branch": branch_id, **filters},
        )


class InventoryHubView(LoginRequiredMixin, View):
    template_name = "inventory/hub.html"

    def get(self, request):
        from core.module_permissions import user_can

        user = request.user
        links = []

        if user_can(user, "inv_grn", "view"):
            links.append(
                {"title": "GRN (Stock Inward)", "desc": "Accounts goods receipt", "url": "inventory:grn"}
            )
        if user_can(user, "inv_outward", "view"):
            links.append(
                {"title": "Outward Register", "desc": "Dispatch stock to branches", "url": "inventory:outward"}
            )
        if user_can(user, "inv_receive", "view"):
            links.append(
                {"title": "Receive Stock", "desc": "Accept branch transfers", "url": "inventory:receive"}
            )
        if user_can(user, "inv_branch_outward", "view"):
            links.append(
                {"title": "Branch Outward", "desc": "Retail sales & consumption", "url": "inventory:branch_outward"}
            )
        if user_can(user, "inv_stock", "view"):
            links.append(
                {"title": "Stock Balance", "desc": "Central & branch stock levels", "url": "inventory:stock"}
            )

        return render(request, self.template_name, {"links": links})
