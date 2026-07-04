from datetime import date, datetime, time
from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone

from inventory.models import (
    BranchOutward,
    Grn,
    GrnStatus,
    OutwardInvoice,
    OutwardRegister,
    OutwardRegisterStatus,
    StockLedger,
    StockRefType,
)
from masters.models import Product

from core.models import Branch


def branch_display_name(branch_id):
    if branch_id is None:
        return "Central (HO)"
    return Branch.objects.get(pk=branch_id).name


def parse_branch_id(raw):
    if not raw or raw == "central":
        return None
    return int(raw)


def parse_date(value):
    if not value:
        return None
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def default_from_date():
    today = timezone.localdate()
    return today.replace(day=1).isoformat()


def default_to_date():
    return timezone.localdate().isoformat()


def _decimal(value):
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def _ledger_qs(branch_id, product_id, *, before=None, from_date=None, to_date=None):
    qs = StockLedger.objects.filter(product_id=product_id)
    if branch_id is None:
        qs = qs.filter(branch__isnull=True)
    else:
        qs = qs.filter(branch_id=branch_id)
    if before is not None:
        qs = qs.filter(created_at__lt=before)
    if from_date is not None:
        qs = qs.filter(created_at__date__gte=from_date)
    if to_date is not None:
        qs = qs.filter(created_at__date__lte=to_date)
    return qs.order_by("created_at", "pk")


def balance_as_of(branch_id, product_id, as_of_date):
    if not as_of_date:
        as_of_date = timezone.localdate()
    end = timezone.make_aware(datetime.combine(as_of_date, time.max))
    result = _ledger_qs(branch_id, product_id, before=end).aggregate(total=Sum("qty_delta"))
    return _decimal(result["total"])


def opening_balance(branch_id, product_id, from_date):
    start = timezone.make_aware(datetime.combine(from_date, time.min))
    result = _ledger_qs(branch_id, product_id, before=start).aggregate(total=Sum("qty_delta"))
    return _decimal(result["total"])


def _particulars_for_entry(entry, cache):
    ref_id = entry.ref_id.split("-")[0]
    try:
        ref_pk = int(ref_id)
    except ValueError:
        ref_pk = ref_id

    if entry.ref_type == StockRefType.GRN:
        grn = cache["grns"].get(ref_pk)
        if grn:
            return f"GRN {grn.grn_number} — {grn.supplier.name}"
        return "GRN"

    if entry.ref_type == StockRefType.OUTWARD_DISPATCH:
        inv = cache["invoices"].get(ref_pk)
        if inv:
            return f"Outward {inv.register.register_number} / {inv.invoice_number} to {inv.branch.name}"
        return "Outward dispatch"

    if entry.ref_type == StockRefType.TRANSFER_RECEIVE:
        inv = cache["invoices"].get(ref_pk)
        if inv:
            return f"Receive stock {inv.invoice_number}"
        return "Receive stock"

    if entry.ref_type == StockRefType.BRANCH_OUTWARD:
        doc = cache["outwards"].get(ref_pk)
        if doc:
            label = doc.get_type_display()
            return f"Branch outward {doc.doc_number} ({label})"
        return "Branch outward"

    return entry.get_ref_type_display()


def _load_ledger_cache(entries):
    grn_ids = set()
    invoice_ids = set()
    outward_ids = set()
    for entry in entries:
        ref_id = entry.ref_id.split("-")[0]
        try:
            ref_pk = int(ref_id)
        except ValueError:
            continue
        if entry.ref_type == StockRefType.GRN:
            grn_ids.add(ref_pk)
        elif entry.ref_type in (StockRefType.OUTWARD_DISPATCH, StockRefType.TRANSFER_RECEIVE):
            invoice_ids.add(ref_pk)
        elif entry.ref_type == StockRefType.BRANCH_OUTWARD:
            outward_ids.add(ref_pk)

    return {
        "grns": {
            g.pk: g
            for g in Grn.objects.filter(pk__in=grn_ids).select_related("supplier")
        },
        "invoices": {
            i.pk: i
            for i in OutwardInvoice.objects.filter(pk__in=invoice_ids).select_related(
                "branch", "register"
            )
        },
        "outwards": {
            o.pk: o
            for o in BranchOutward.objects.filter(pk__in=outward_ids).select_related("branch")
        },
    }


def build_inventory_statement(branch_id, product_id, from_date, to_date):
    headers = ["Date", "Particulars", "In", "Out", "Closing stock"]
    if branch_id is None:
        allowed = {StockRefType.GRN, StockRefType.OUTWARD_DISPATCH}
    else:
        allowed = {StockRefType.TRANSFER_RECEIVE, StockRefType.BRANCH_OUTWARD}

    opening = opening_balance(branch_id, product_id, from_date)
    rows = [
        [from_date, "Opening balance", "", "", float(opening)],
    ]
    balance = opening

    entries = list(
        _ledger_qs(branch_id, product_id, from_date=from_date, to_date=to_date).filter(
            ref_type__in=allowed
        )
    )
    cache = _load_ledger_cache(entries)

    for entry in entries:
        delta = _decimal(entry.qty_delta)
        in_qty = float(delta) if delta > 0 else ""
        out_qty = float(abs(delta)) if delta < 0 else ""
        balance += delta
        rows.append(
            [
                entry.created_at.date(),
                _particulars_for_entry(entry, cache),
                in_qty,
                out_qty,
                float(balance),
            ]
        )

    if not entries:
        rows.append([to_date, "No movements in period", "", "", float(balance)])

    return headers, rows


def build_grn_report(product_id, from_date, to_date):
    headers = ["Date", "GRN No", "Supplier name", "No of stock"]
    rows = []
    qs = (
        Grn.objects.filter(status=GrnStatus.POSTED, date__gte=from_date, date__lte=to_date)
        .select_related("supplier")
        .prefetch_related("lines")
        .order_by("date", "grn_number")
    )
    for grn in qs:
        qty = sum(
            (line.quantity for line in grn.lines.all() if line.product_id == product_id),
            Decimal("0"),
        )
        if qty <= 0:
            continue
        rows.append([grn.date, grn.grn_number, grn.supplier.name, float(qty)])
    return headers, rows


def build_outward_register_report(product_id, from_date, to_date):
    headers = ["Date", "Outward No", "Branch name", "No of stock"]
    rows = []
    registers = (
        OutwardRegister.objects.filter(
            status=OutwardRegisterStatus.DISPATCHED,
            date__gte=from_date,
            date__lte=to_date,
        )
        .prefetch_related("invoices__lines", "invoices__branch")
        .order_by("date", "register_number")
    )
    for reg in registers:
        for inv in reg.invoices.all():
            qty = sum(
                (line.quantity_sent for line in inv.lines.all() if line.product_id == product_id),
                Decimal("0"),
            )
            if qty <= 0:
                continue
            rows.append([reg.date, reg.register_number, inv.branch.name, float(qty)])
    return headers, rows


def build_receive_stock_report(product_id, from_date, to_date, branch_id=None):
    headers = ["Date", "Receive stock No", "Branch", "Qty"]
    rows = []
    qs = StockLedger.objects.filter(
        ref_type=StockRefType.TRANSFER_RECEIVE,
        product_id=product_id,
        created_at__date__gte=from_date,
        created_at__date__lte=to_date,
    ).select_related("branch")
    if branch_id is not None:
        qs = qs.filter(branch_id=branch_id)

    invoice_ids = set()
    for entry in qs.order_by("created_at"):
        try:
            invoice_ids.add(int(entry.ref_id.split("-")[0]))
        except ValueError:
            pass
    invoices = {
        i.pk: i
        for i in OutwardInvoice.objects.filter(pk__in=invoice_ids).select_related("branch")
    }

    for entry in qs.order_by("created_at"):
        try:
            inv_pk = int(entry.ref_id.split("-")[0])
        except ValueError:
            inv_pk = None
        inv = invoices.get(inv_pk)
        receive_no = inv.invoice_number if inv else entry.ref_id
        branch_name = entry.branch.name if entry.branch else (inv.branch.name if inv else "—")
        rows.append(
            [
                entry.created_at.date(),
                receive_no,
                branch_name,
                float(entry.qty_delta),
            ]
        )
    return headers, rows


def build_branch_outward_report(product_id, from_date, to_date, branch_id=None):
    headers = ["Date", "Branch outward No", "Branch name", "Qty"]
    rows = []
    qs = BranchOutward.objects.filter(
        date__date__gte=from_date,
        date__date__lte=to_date,
    ).prefetch_related("lines").select_related("branch")
    if branch_id is not None:
        qs = qs.filter(branch_id=branch_id)
    qs = qs.order_by("date", "doc_number")
    for doc in qs:
        qty = sum(
            (line.quantity for line in doc.lines.all() if line.product_id == product_id),
            Decimal("0"),
        )
        if qty <= 0:
            continue
        rows.append([doc.date.date(), doc.doc_number, doc.branch.name, float(qty)])
    return headers, rows


def build_stock_balance_report(branch_id, product_id, as_of_date):
    headers = ["Branch", "Inventory name", "Category", "Qty", "Unit"]
    rows = []
    products = Product.objects.filter(active=True).select_related("inventory_category")
    if product_id:
        products = products.filter(pk=product_id)

    branch_label = branch_display_name(branch_id)

    for product in products.order_by("name"):
        qty = balance_as_of(branch_id, product.pk, as_of_date)
        rows.append(
            [
                branch_label,
                product.name,
                product.inventory_category.name,
                float(qty),
                product.unit,
            ]
        )
    return headers, rows


REPORT_TYPES = (
    ("statement", "Inventory Statement"),
    ("grn", "GRN Report"),
    ("outward", "Outward Register"),
    ("receive", "Receive Stock"),
    ("branch-outward", "Branch Outward"),
    ("stock-balance", "Stock Balance"),
)


def build_report(report_type, *, branch_id, product_id, from_date, to_date, as_of_date):
    from_date = parse_date(from_date)
    to_date = parse_date(to_date)
    as_of_date = parse_date(as_of_date)

    if report_type == "statement":
        if product_id is None or from_date is None or to_date is None:
            return ["Date", "Particulars", "In", "Out", "Closing stock"], []
        return build_inventory_statement(branch_id, product_id, from_date, to_date)

    if report_type == "grn":
        if product_id is None or from_date is None or to_date is None:
            return ["Date", "GRN No", "Supplier name", "No of stock"], []
        return build_grn_report(product_id, from_date, to_date)

    if report_type == "outward":
        if product_id is None or from_date is None or to_date is None:
            return ["Date", "Outward No", "Branch name", "No of stock"], []
        return build_outward_register_report(product_id, from_date, to_date)

    if report_type == "receive":
        if product_id is None or from_date is None or to_date is None:
            return ["Date", "Receive stock No", "Branch", "Qty"], []
        return build_receive_stock_report(product_id, from_date, to_date, branch_id)

    if report_type == "branch-outward":
        if product_id is None or from_date is None or to_date is None:
            return ["Date", "Branch outward No", "Branch name", "Qty"], []
        return build_branch_outward_report(product_id, from_date, to_date, branch_id)

    if report_type == "stock-balance":
        if as_of_date is None:
            as_of_date = timezone.localdate()
        return build_stock_balance_report(branch_id, product_id, as_of_date)

    return [], []
