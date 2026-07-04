from decimal import Decimal

from .models import PettyCashTransaction


def build_petty_cash_report(queryset):
    """Return rows with running balance: date, particulars, payments, receipts, balance."""
    txs = queryset.order_by("entry_date", "created_at")
    balance = Decimal("0")
    rows = []
    for tx in txs:
        payment = (
            tx.amount
            if tx.transaction_type == PettyCashTransaction.Type.PAYMENT
            else Decimal("0")
        )
        # Opening balance and receipts both increase cash on hand
        receipt = (
            tx.amount
            if tx.transaction_type
            in (PettyCashTransaction.Type.RECEIPT, PettyCashTransaction.Type.OPENING)
            else Decimal("0")
        )
        balance += receipt - payment
        rows.append(
            {
                "date": tx.entry_date,
                "particulars": tx.display_particulars,
                "payments": payment if payment else "",
                "receipts": receipt if receipt else "",
                "balance": balance,
                "branch": tx.branch.name,
                "is_opening": tx.transaction_type == PettyCashTransaction.Type.OPENING,
            }
        )
    return rows
