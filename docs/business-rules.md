# Salon MIS — Business Rules (defaults)

These defaults apply until overridden by uploaded report templates or admin configuration.

## Transfer acceptance

- **Partial acceptance is allowed.** Branch can accept received quantity per line (e.g. 8 of 10).
- Shortage/damage is recorded in `shortageRemarks` on acceptance.
- Invoice status becomes `PARTIALLY_RECEIVED` or `RECEIVED` accordingly.
- Only accepted quantity is added to branch stock.

## DSR scope

- Includes **retail product sales** and **salon service revenue**.
- Payment split: cash, card, UPI.
- Customer counts: total, male, female.

## Pricing

- Products track **purchase rate** (GRN) and **selling price** (retail outward / DSR).

## Branches

- System supports **unlimited branches**; seed data includes 2 sample branches.

## Stock

- Central stock: `branchId = null` in ledger.
- Branch stock: `branchId` set.
- Insufficient stock blocks branch outward unless user is `BRANCH_MANAGER` or `SUPER_ADMIN`.
