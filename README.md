# Gumroad & Stripe Seller Ledger

**Price target:** $19 (premium $27 with quarterly checklist)  
**Channel:** Gumroad  
**Differentiator:** Platform-fee-aware P&L from Gumroad + Stripe CSV exports — not a generic budget sheet, not a clone of Solo Freelancer Cashflow Kit.

---

## What the buyer gets

### Docs
| File | Role |
|------|------|
| `LISTING.md` | Gumroad paste-ready copy |
| `SETUP.md` | Fast Sheets + CLI path |
| `sops/SETUP-SOP.md` | Longer setup SOP (~15 min) |
| `sops/MONTHLY-CLOSE-SELLER.md` | Monthly seller close ritual |
| `QUARTERLY-TAX-CHECKLIST.md` | Premium add-on checklist |

### Schemas (Sheets-friendly CSV headers)
| File | Role |
|------|------|
| `schemas/gumroad_sales_schema.csv` | Gumroad sales export columns (cents-aware) |
| `schemas/stripe_balance_schema.csv` | Stripe balance-transaction columns |
| `schemas/unified_seller_ledger_schema.csv` | Normalized ledger output columns |
| `schemas/category_map.csv` | Product/description → category |
| `schemas/gumroad-payout-import.csv` | Alternate simple payout paste headers |
| `schemas/stripe-payout-import.csv` | Alternate simple payout paste headers |

### Samples
| File | Role |
|------|------|
| `samples/sample_gumroad_sales.csv` | Demo Gumroad sales (cents) |
| `samples/sample_stripe_balance.csv` | Demo Stripe balance txns |
| `samples/sample-gumroad-payouts.csv` | Demo simple payout paste format |
| `samples/sample-stripe-payouts.csv` | Demo simple payout paste format |

### Calculators (Python 3, stdlib only)
| Script | Role |
|------|------|
| `scripts/seller_ledger_pnl.py` | **Primary** — fee-aware monthly/Q/YTD P&L + category rollup + tax set-aside |
| `scripts/seller_ledger.py` | Simple payout-CSV → `monthly_pnl.csv` + safe-to-spend |
| `scripts/payout_fee_audit.py` | Fee sanity check helper |

---

## Quick start (2 minutes)

```bash
cd scripts
python3 seller_ledger_pnl.py \
  --gumroad ../samples/sample_gumroad_sales.csv \
  --stripe ../samples/sample_stripe_balance.csv \
  --category-map ../schemas/category_map.csv \
  --tax-rate 0.30
```

Or: `python3 seller_ledger.py --gumroad ../samples/sample-gumroad-payouts.csv --stripe ../samples/sample-stripe-payouts.csv --tax-rate 0.30 --fixed-costs 400 --out ../samples/out`

---

## Disclaimer

Planning tool only. **Not tax advice.** Platform fees change — verify against live statements. Confirm estimates with a CPA.
