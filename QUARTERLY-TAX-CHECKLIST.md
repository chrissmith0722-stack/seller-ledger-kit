# Quarterly Tax Checklist (Seller Ledger premium add-on)

**Not tax advice.** Use with your CPA / tax software. Dates below are typical U.S. federal estimated-tax due dates — confirm current-year IRS calendar.

## Before each quarter closes
- [ ] Export fresh Gumroad + Stripe CSVs; re-run ledger (or refresh Sheets imports)
- [ ] Reconcile refunds/chargebacks so net is not overstated
- [ ] Confirm fee totals roughly match platform dashboards (± small timing diffs OK)
- [ ] Update `tax_rate` if your CPA gave a new effective rate
- [ ] Update monthly fixed costs (software, rent share, health premium, etc.)

## Estimated payment ritual
- [ ] Read YTD net and YTD tax_set_aside from ledger output
- [ ] Subtract amounts already paid this year for federal (and state if applicable)
- [ ] Transfer remaining set-aside to a separate savings/"tax lockbox" account
- [ ] Pay estimated tax via IRS Direct Pay / EFTPS (and state portal) by due date
- [ ] Log confirmation number + amount in a simple payments log

## Typical federal due dates (verify annually)
| Period | Income months (calendar year) | Typical due |
|--------|-------------------------------|-------------|
| Q1 | Jan–Mar | mid-April |
| Q2 | Apr–May | mid-June |
| Q3 | Jun–Aug | mid-September |
| Q4 | Sep–Dec | mid-January (following year) |

## Year-end handoff to CPA
- [ ] Annual `monthly_pnl.csv` export
- [ ] 1099-K / 1099-NEC forms when received
- [ ] Expense export from your bookkeeping system (Cashflow Kit or other)
- [ ] Note any large one-time refunds or chargebacks
