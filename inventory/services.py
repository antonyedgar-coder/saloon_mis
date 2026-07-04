from decimal import Decimal

from django.db import transaction

from core.models import DocumentSequence

from masters.models import Product

from .models import (
    Grn,
    GrnLine,
    GrnStatus,
    OutwardInvoice,
    OutwardInvoiceLine,
    OutwardInvoiceStatus,
    OutwardRegisterStatus,
    StockLedger,
    StockRefType,
    TransferAcceptance,
)


@transaction.atomic
def reverse_grn_stock(grn: Grn, user):
    if grn.status != GrnStatus.POSTED:
        return
    lines = list(grn.lines.all())
    if lines:
        StockLedger.assert_central_sufficient(
            [{"product_id": line.product_id, "quantity": line.quantity} for line in lines]
        )
        StockLedger.add_entries(
            [
                {
                    "branch_id": None,
                    "product_id": line.product_id,
                    "qty_delta": -line.quantity,
                    "ref_type": StockRefType.GRN,
                    "ref_id": f"{grn.pk}-rev",
                }
                for line in lines
            ],
            user,
        )
    grn.status = GrnStatus.DRAFT
    grn.save(update_fields=["status"])


@transaction.atomic
def delete_grn(grn: Grn, user):
    reverse_grn_stock(grn, user)
    grn.delete()


@transaction.atomic
def update_grn(grn: Grn, user, *, date, supplier_id, supplier_invoice, lines):
    reverse_grn_stock(grn, user)
    grn.date = date
    grn.supplier_id = supplier_id
    grn.supplier_invoice = supplier_invoice
    grn.save(update_fields=["date", "supplier_id", "supplier_invoice"])
    grn.lines.all().delete()
    for line in lines:
        product = Product.objects.get(pk=line["product_id"])
        rate = product.purchase_rate if product.purchase_rate is not None else Decimal("0")
        GrnLine.objects.create(
            grn=grn,
            product_id=line["product_id"],
            quantity=line["quantity"],
            rate=rate,
        )
    post_grn(grn, user)


@transaction.atomic
def post_grn(grn: Grn, user):
    if grn.status == GrnStatus.POSTED:
        raise ValueError("GRN already posted")
    grn.status = GrnStatus.POSTED
    grn.save(update_fields=["status"])
    StockLedger.add_entries(
        [
            {
                "branch_id": None,
                "product_id": line.product_id,
                "qty_delta": line.quantity,
                "ref_type": StockRefType.GRN,
                "ref_id": grn.pk,
            }
            for line in grn.lines.all()
        ],
        user,
    )


@transaction.atomic
def dispatch_outward(register, invoices_data, user):
    all_lines = []
    for inv in invoices_data:
        all_lines.extend(inv["lines"])

    StockLedger.assert_central_sufficient(
        [{"product_id": l["product_id"], "quantity": l["quantity_sent"]} for l in all_lines]
    )

    register.status = OutwardRegisterStatus.DISPATCHED
    register.save(update_fields=["status"])

    ledger_entries = []
    for inv_data in invoices_data:
        invoice = OutwardInvoice.objects.create(
            invoice_number=DocumentSequence.next_number("OI"),
            register=register,
            branch_id=inv_data["branch_id"],
            status=OutwardInvoiceStatus.DISPATCHED,
            remarks=inv_data.get("remarks", ""),
        )
        for line in inv_data["lines"]:
            OutwardInvoiceLine.objects.create(
                invoice=invoice,
                product_id=line["product_id"],
                quantity_sent=line["quantity_sent"],
            )
            ledger_entries.append(
                {
                    "branch_id": None,
                    "product_id": line["product_id"],
                    "qty_delta": -line["quantity_sent"],
                    "ref_type": StockRefType.OUTWARD_DISPATCH,
                    "ref_id": invoice.pk,
                }
            )

    StockLedger.add_entries(ledger_entries, user)
    return register


@transaction.atomic
def accept_transfer_line(invoice, line, qty_received, user, expiry_date=None):
    if line.quantity_received >= line.quantity_sent:
        raise ValueError(f"{line.product.name} is already accepted")

    qty_received = Decimal(str(qty_received or 0))
    if qty_received <= 0:
        raise ValueError("Quantity must be greater than zero")
    if qty_received > line.quantity_sent:
        raise ValueError(f"Received qty exceeds sent for {line.product.name}")

    if expiry_date:
        line.expiry_date = expiry_date
    if not line.expiry_date:
        raise ValueError(
            f"Enter expiry date for {line.product.name} before accepting stock."
        )

    line.quantity_received = qty_received
    line.save(update_fields=["quantity_received", "expiry_date"])

    StockLedger.add_entries(
        [
            {
                "branch_id": invoice.branch_id,
                "product_id": line.product_id,
                "qty_delta": qty_received,
                "ref_type": StockRefType.TRANSFER_RECEIVE,
                "ref_id": invoice.pk,
            }
        ],
        user,
    )

    lines = list(invoice.lines.all())
    if all(l.quantity_received >= l.quantity_sent for l in lines):
        invoice.status = OutwardInvoiceStatus.RECEIVED
    else:
        invoice.status = OutwardInvoiceStatus.PARTIALLY_RECEIVED
    invoice.save(update_fields=["status"])


@transaction.atomic
def accept_transfer(invoice, line_receipts, user, remarks="", shortage_remarks=""):
    if invoice.status == OutwardInvoiceStatus.RECEIVED:
        raise ValueError("Invoice already received")

    ledger_entries = []
    for line_id, qty_received in line_receipts.items():
        qty_received = Decimal(str(qty_received or 0))
        line = invoice.lines.get(pk=line_id)
        if qty_received > line.quantity_sent:
            raise ValueError(f"Received qty exceeds sent for {line.product.name}")
        if not line.expiry_date:
            raise ValueError(
                f"Enter expiry date for {line.product.name} before accepting stock."
            )
        line.quantity_received = qty_received
        line.save(update_fields=["quantity_received"])
        if qty_received > 0:
            ledger_entries.append(
                {
                    "branch_id": invoice.branch_id,
                    "product_id": line.product_id,
                    "qty_delta": qty_received,
                    "ref_type": StockRefType.TRANSFER_RECEIVE,
                    "ref_id": invoice.pk,
                }
            )

    lines = list(invoice.lines.all())
    all_full = all(line.quantity_received == line.quantity_sent for line in lines)
    any_received = any(line.quantity_received > 0 for line in lines)
    if all_full:
        invoice.status = OutwardInvoiceStatus.RECEIVED
    elif any_received:
        invoice.status = OutwardInvoiceStatus.PARTIALLY_RECEIVED
    invoice.save(update_fields=["status"])

    TransferAcceptance.objects.create(
        invoice=invoice,
        remarks=remarks,
        shortage_remarks=shortage_remarks,
    )
    StockLedger.add_entries(ledger_entries, user)
