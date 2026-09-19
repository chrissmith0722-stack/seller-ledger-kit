# Setup SOP — Gumroad & Stripe Seller Ledger (≈15 minutes)

**Goal:** Import real (or sample) payout CSVs and see fee-aware net + tax set-aside.  
**Not tax advice.** Confirm figures with a CPA / tax software before filing.

## Prerequisites
- Python 3.9+ (stdlib only — no pip packages required)
- Gumroad and/or Stripe account with CSV export access
- This kit folder on disk

## Steps

### 1. Smoke-test with samples (2 min)
```bash
cd scripts
python3 seller_ledger_pnl.py \
  --gumroad ../samples/sample_gumroad_sales.csv \
  --stripe ../samples/sample_stripe_balance.csv \
  --category-map ../schemas/category_map.csv \
  --tax-rate 0.30 \
  --write-ledger /tmp/unified_ledger.csv

python3 payout_fee_audit.py --ledger /tmp/unified_ledger.csv
```
You should see Monthly / Quarterly / By-category tables and a YTD snapshot.

### 2. Export Gumroad sales CSV
1. Gumroad → **Sales** (or **Payouts**) → Export / Download CSV  
2. Save as `data/gumroad_YYYY-MM.csv`  
3. Confirm columns match `schemas/gumroad_sales_schema.csv` (rename headers if needed: `sale_id`, `sale_date`, `product_name`, `price_cents`, `gumroad_fee_cents`, `net_cents`, …)

### 3. Export Stripe balance transactions
1. Stripe Dashboard → **Balances** → **Balance transactions** → Export  
   (or **Payouts** → open a payout → related transactions)  
2. Save as `data/stripe_YYYY-MM.csv`  
3. Confirm columns align with `schemas/stripe_balance_schema.csv` (`id`, `Created (UTC)`, `Amount`, `Fee`, `Net`, `Description`, `Type`)

### 4. Tune category map
Edit `schemas/category_map.csv` — add your product name substrings → `digital_products`, `subscriptions`, `freelance_invoices`, `tips`, etc. First match wins; keep `*,other` last.

### 5. Run on your data
```bash
python3 seller_ledger_pnl.py \
  --gumroad ../data/gumroad_YYYY-MM.csv \
  --stripe ../data/stripe_YYYY-MM.csv \
  --category-map ../schemas/category_map.csv \
  --tax-rate 0.28 \
  --write-ledger ../data/unified_ledger.csv
```
Adjust `--tax-rate` to your CPA’s planning rate (often 25–35% for US sole props — **illustrative only**).

### 6. Weekly / monthly cadence
| When | Action |
|------|--------|
| Weekly | Re-export CSVs; re-run P&L; scan `payout_fee_audit.py` flags |
| Month-end | Archive `unified_ledger.csv` as `ledger_YYYY-MM.csv` |
| Quarter-end | Hand YTD net + fees to tax estimator (see Quarterly Tax Dashboard kit) |

## What this is / isn’t
| This kit | Cashflow Kit (separate SKU) |
|----------|------------------------------|
| Platform CSV → fee P&L | Monthly income / expense / invoice close |
| Gumroad + Stripe native columns | Generic freelancer ledgers |
| Seller category mapper | Budget categories |

## Troubleshooting
- **Wrong fees:** Gumroad may export dollars vs cents — script auto-detects decimals.  
- **Missing net:** Script recomputes `gross − fee − refunds`.  
- **Payouts in net:** Payout rows are categorized `payouts` and excluded from P&L totals.  
- **Encoding:** Files with BOM are supported (`utf-8-sig`).
