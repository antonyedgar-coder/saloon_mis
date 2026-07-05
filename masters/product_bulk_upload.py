from django.db import transaction

from core.bulk_upload_utils import (
    cell_text,
    find_column_index,
    read_tabular_upload,
)
from masters.models import InventoryCategory, Product


PRODUCT_HEADERS = ["Inventory Name", "Inventory Category"]


def parse_product_upload(uploaded_file):
    rows = read_tabular_upload(uploaded_file)
    if not rows:
        raise ValueError("The file is empty.")

    headers = [str(cell) for cell in rows[0]]
    name_idx = find_column_index(headers, "inventory name", "name")
    category_idx = find_column_index(headers, "inventory category", "category")
    if name_idx is None or category_idx is None:
        raise ValueError(
            "Header row must include columns: Inventory Name, Inventory Category."
        )

    parsed_rows = []
    errors = []
    for row_number, row in enumerate(rows[1:], start=2):
        name = cell_text(row, name_idx)
        category_name = cell_text(row, category_idx)
        if not name and not category_name:
            continue
        if not name:
            errors.append(f"Row {row_number}: Inventory Name is required.")
            continue
        if not category_name:
            errors.append(f"Row {row_number}: Inventory Category is required.")
            continue
        parsed_rows.append(
            {
                "row_number": row_number,
                "name": name,
                "category_name": category_name,
            }
        )

    if errors:
        raise ValueError("\n".join(errors))
    if not parsed_rows:
        raise ValueError("No product rows found in the file.")
    return parsed_rows


@transaction.atomic
def apply_product_upload(parsed_rows):
    created = 0
    updated = 0
    skipped = 0
    errors = []

    categories = {
        category.name.strip().lower(): category
        for category in InventoryCategory.objects.filter(active=True)
    }

    for row in parsed_rows:
        category = categories.get(row["category_name"].lower())
        if not category:
            errors.append(
                f"Row {row['row_number']}: Inventory Category "
                f"'{row['category_name']}' was not found."
            )
            continue

        product = Product.objects.filter(name__iexact=row["name"]).first()
        if product:
            if product.inventory_category_id != category.pk:
                product.inventory_category = category
                product.save(update_fields=["inventory_category"])
                updated += 1
            else:
                skipped += 1
            continue

        Product.objects.create(
            name=row["name"],
            inventory_category=category,
            unit="pcs",
        )
        created += 1

    if errors:
        raise ValueError("\n".join(errors))

    return {"created": created, "updated": updated, "skipped": skipped}
