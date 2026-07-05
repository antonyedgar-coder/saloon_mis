from collections import defaultdict
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from core.bulk_upload_utils import (
    cell_text,
    find_column_index,
    parse_decimal,
    parse_required_date,
    read_tabular_upload,
)
from core.models import Branch
from inventory.models import OpeningStockLine, OpeningStockUpload, StockLedger, StockRefType
from masters.models import Product


OPENING_STOCK_HEADERS = ["Branch", "Inventory Name", "Quantity", "Expiry Date"]
CENTRAL_BRANCH_ALIASES = {"central", "ho", "head office", "headoffice", "central (ho)"}


def _resolve_branch_id(branch_label):
    label = (branch_label or "").strip()
    if not label or label.lower() in CENTRAL_BRANCH_ALIASES:
        return None
    branch = Branch.objects.filter(name__iexact=label, active=True).first()
    if not branch:
        raise ValueError(f"Branch '{branch_label}' was not found.")
    return branch.pk


def parse_opening_stock_upload(uploaded_file):
    rows = read_tabular_upload(uploaded_file)
    if not rows:
        raise ValueError("The file is empty.")

    headers = [str(cell) for cell in rows[0]]
    branch_idx = find_column_index(headers, "branch", "branch name", "location")
    name_idx = find_column_index(headers, "inventory name", "name")
    qty_idx = find_column_index(headers, "quantity", "qty")
    expiry_idx = find_column_index(headers, "expiry date", "expiry")
    if branch_idx is None or name_idx is None or qty_idx is None or expiry_idx is None:
        raise ValueError(
            "Header row must include columns: Branch, Inventory Name, Quantity, Expiry Date."
        )

    parsed_rows = []
    errors = []
    for row_number, row in enumerate(rows[1:], start=2):
        branch_label = cell_text(row, branch_idx)
        name = cell_text(row, name_idx)
        if not branch_label and not name:
            continue
        if not branch_label:
            errors.append(f"Row {row_number}: Branch is required.")
            continue
        if not name:
            errors.append(f"Row {row_number}: Inventory Name is required.")
            continue
        try:
            branch_id = _resolve_branch_id(branch_label)
            quantity = parse_decimal(cell_text(row, qty_idx), "Quantity", row_number)
            expiry_date = parse_required_date(
                row[expiry_idx] if expiry_idx < len(row) else "",
                "Expiry Date",
                row_number,
            )
        except ValueError as exc:
            errors.append(str(exc))
            continue
        if quantity == 0:
            errors.append(f"Row {row_number}: Quantity must be greater than zero.")
            continue
        parsed_rows.append(
            {
                "row_number": row_number,
                "branch_id": branch_id,
                "branch_label": branch_label,
                "name": name,
                "quantity": quantity,
                "expiry_date": expiry_date,
            }
        )

    if errors:
        raise ValueError("\n".join(errors))
    if not parsed_rows:
        raise ValueError("No opening stock rows found in the file.")
    return parsed_rows


def _resolve_products(parsed_rows):
    products = {
        product.name.strip().lower(): product
        for product in Product.objects.filter(active=True)
    }
    resolved = []
    errors = []
    for row in parsed_rows:
        product = products.get(row["name"].lower())
        if not product:
            errors.append(
                f"Row {row['row_number']}: Inventory Name '{row['name']}' was not found."
            )
            continue
        resolved.append({**row, "product": product})
    if errors:
        raise ValueError("\n".join(errors))
    return resolved


def _allowed_branch_ids(user):
    if user.is_central():
        return None
    return set(user.branch_ids())


@transaction.atomic
def apply_opening_stock_upload(*, parsed_rows, stock_date, user):
    if stock_date is None:
        stock_date = timezone.localdate()

    allowed = _allowed_branch_ids(user)
    lines = _resolve_products(parsed_rows)

    grouped = defaultdict(list)
    for line in lines:
        if allowed is not None and line["branch_id"] not in allowed:
            raise ValueError(
                f"Row {line['row_number']}: you cannot upload opening stock for "
                f"'{line['branch_label']}'."
            )
        grouped[line["branch_id"]].append(line)

    branch_count = 0
    line_count = 0
    total_qty = Decimal("0")

    for branch_id, branch_lines in grouped.items():
        previous_uploads = OpeningStockUpload.objects.filter(branch_id=branch_id)
        previous_ids = list(previous_uploads.values_list("pk", flat=True))
        if previous_ids:
            StockLedger.objects.filter(
                ref_type=StockRefType.OPENING_STOCK,
                ref_id__in=[str(pk) for pk in previous_ids],
            ).delete()
            previous_uploads.delete()

        upload = OpeningStockUpload.objects.create(
            branch_id=branch_id,
            stock_date=stock_date,
            created_by=user,
        )
        ledger_entries = []
        for line in branch_lines:
            OpeningStockLine.objects.create(
                upload=upload,
                product=line["product"],
                quantity=line["quantity"],
                expiry_date=line["expiry_date"],
            )
            ledger_entries.append(
                {
                    "branch_id": branch_id,
                    "product_id": line["product"].pk,
                    "qty_delta": line["quantity"],
                    "ref_type": StockRefType.OPENING_STOCK,
                    "ref_id": str(upload.pk),
                }
            )
            line_count += 1
            total_qty += line["quantity"]

        StockLedger.add_entries(ledger_entries, user)
        branch_count += 1

    return {
        "branches": branch_count,
        "lines": line_count,
        "total_qty": total_qty,
        "stock_date": stock_date,
    }
