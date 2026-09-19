# Monthly Close SOP — Platform Sellers (Gumroad / Stripe)

Use alongside (not instead of) a general bookkeeping close. Focus: **platform fees, refunds, chargebacks**.

## Checklist
- [ ] Export Gumroad sales CSV for the closed month  
- [ ] Export Stripe balance transactions for the closed month  
- [ ] Run `seller_ledger_pnl.py` → save `data/ledger_YYYY-MM.csv`  
- [ ] Run `payout_fee_audit.py` — investigate HIGH_FEE / NET_MISMATCH  
- [ ] Confirm refund + chargeback totals match dashboard  
- [ ] Note any promo / offer codes that distorted fee %  
- [ ] Update tax set-aside: `YTD net × planning rate` → transfer to tax savings account  
- [ ] Record bank payout arrivals (Stripe/Gumroad payout rows) vs bank statement  
- [ ] Archive CSVs + ledger zip for the month  

## Outputs to keep
1. Raw platform CSVs  
2. Unified ledger CSV  
3. Screenshot or text dump of Monthly P&L table  
4. Tax set-aside transfer confirmation  

**Disclaimer:** Planning workflow only — not CPA, legal, or tax advice.
