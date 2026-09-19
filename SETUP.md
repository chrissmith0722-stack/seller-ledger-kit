# Setup — Seller Ledger (≈10 minutes)

## Option A — Google Sheets (no code)

1. Create a new Google Sheet named `Seller Ledger — Master`.
2. Create tabs: `Gumroad_Import`, `Stripe_Import`, `Category_Map`, `Monthly_PnL`, `Dashboard`.
3. Row 1 headers — copy exactly from:
   - `schemas/gumroad-payout-import.csv`
   - `schemas/stripe-payout-import.csv`
   - `schemas/category-map.csv`
4. File → Import → Upload each `samples/*.csv` into the matching tab (Append or Replace).
5. On `Monthly_PnL`, add columns: `month`, `gross`, `fees`, `refunds`, `net`, `tax_set_aside`, `safe_to_spend`.
6. Suggested Sheets formulas (row 2 example, adjust ranges):

```
net = gross - fees - refunds
tax_set_aside = net * tax_rate          // put tax_rate in Dashboard!B1 (e.g. 0.30)
safe_to_spend = net - tax_set_aside - fixed_costs
```

7. Pivot or `SUMIF` by `month` from the import tabs into `Monthly_PnL`.
8. Dashboard: show YTD net, YTD fees, YTD set-aside, current safe-to-spend.

**Fee columns:** Prefer using the fee amounts from your export when present. If a row has blank fees, apply a fallback % in a helper column (Gumroad often ~10% + processing; Stripe varies — do not hard-code blindly).

## Option B — Python CLI

```bash
python3 scripts/seller_ledger.py --help
python3 scripts/seller_ledger.py \
  --gumroad path/to/gumroad.csv \
  --stripe path/to/stripe.csv \
  --tax-rate 0.30 \
  --fixed-costs 500 \
  --out ./out
```

Writes `out/monthly_pnl.csv` and prints a summary.

## Exporting from platforms

**Gumroad:** Library / Payouts → export CSV (or Sales CSV). Map columns to the schema; rename headers if Gumroad’s labels differ slightly year-to-year.

**Stripe:** Payments → Export, or Balance → Payouts → CSV. Map `Amount`, `Fee`, `Net`, `Created`, `Description`, `Type`.

## Replace sample data

Delete sample rows after you’ve confirmed formulas/CLI output look right. Keep one fictional row as a formula sanity check if you want.
