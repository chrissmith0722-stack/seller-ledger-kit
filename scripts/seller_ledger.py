#!/usr/bin/env python3
"""
Gumroad + Stripe Seller Ledger
------------------------------
Import payout CSVs → monthly P&L (gross, fees, refunds, net),
quarterly tax set-aside estimate, and safe-to-spend.

Not tax advice. Fee columns preferred over guessed percentages.
"""
from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple


Number = float


def _f(row: dict, *keys: str, default: float = 0.0) -> Number:
    for k in keys:
        if k in row and row[k] not in (None, ""):
            try:
                return float(str(row[k]).replace(",", "").replace("$", "").strip())
            except ValueError:
                continue
    return default


def _month(date_str: str) -> str:
    s = (date_str or "").strip()
    if len(s) >= 7 and s[4] == "-":
        return s[:7]  # YYYY-MM
    return "unknown"


def load_csv(path: Path) -> List[dict]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def accumulate(
    rows: Iterable[dict],
    date_key: str,
    source: str,
) -> Dict[str, Dict[str, Number]]:
    """Return month -> {gross, fees, refunds, net, count}."""
    buckets: Dict[str, Dict[str, Number]] = defaultdict(
        lambda: {"gross": 0.0, "fees": 0.0, "refunds": 0.0, "net": 0.0, "count": 0.0}
    )
    for row in rows:
        m = _month(row.get(date_key, ""))
        gross = _f(row, "gross_usd", "gross")
        fees = _f(row, "fee_usd", "fees", "fee")
        refunds = _f(row, "refund_usd", "refunds", "refund")
        net = _f(row, "net_usd", "net", default=None)  # type: ignore
        if net is None:
            net = gross - fees - refunds
        # Stripe refund rows often carry negative net and refund_usd > 0
        b = buckets[m]
        b["gross"] += gross
        b["fees"] += fees
        b["refunds"] += refunds
        b["net"] += net
        b["count"] += 1
        b.setdefault("_sources", 0)
    # tag source counts lightly via side channel not needed for CSV
    return buckets


def merge_buckets(
    *parts: Tuple[str, Dict[str, Dict[str, Number]]]
) -> Dict[str, Dict[str, Number]]:
    out: Dict[str, Dict[str, Number]] = defaultdict(
        lambda: {
            "gross": 0.0,
            "fees": 0.0,
            "refunds": 0.0,
            "net": 0.0,
            "count": 0.0,
            "gumroad_net": 0.0,
            "stripe_net": 0.0,
        }
    )
    for label, buckets in parts:
        for m, b in buckets.items():
            o = out[m]
            for k in ("gross", "fees", "refunds", "net", "count"):
                o[k] += b[k]
            if label == "gumroad":
                o["gumroad_net"] += b["net"]
            elif label == "stripe":
                o["stripe_net"] += b["net"]
    return out


def write_monthly_pnl(
    path: Path,
    monthly: Dict[str, Dict[str, Number]],
    tax_rate: float,
    fixed_costs: float,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "month",
        "gross",
        "fees",
        "refunds",
        "net",
        "gumroad_net",
        "stripe_net",
        "tax_set_aside",
        "fixed_costs",
        "safe_to_spend",
        "transaction_count",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for m in sorted(monthly.keys()):
            b = monthly[m]
            net = b["net"]
            set_aside = round(net * tax_rate, 2)
            # fixed_costs applied per month (edit if you prefer annual/12)
            safe = round(net - set_aside - fixed_costs, 2)
            w.writerow(
                {
                    "month": m,
                    "gross": round(b["gross"], 2),
                    "fees": round(b["fees"], 2),
                    "refunds": round(b["refunds"], 2),
                    "net": round(net, 2),
                    "gumroad_net": round(b.get("gumroad_net", 0.0), 2),
                    "stripe_net": round(b.get("stripe_net", 0.0), 2),
                    "tax_set_aside": set_aside,
                    "fixed_costs": fixed_costs,
                    "safe_to_spend": safe,
                    "transaction_count": int(b["count"]),
                }
            )


def summarize(
    monthly: Dict[str, Dict[str, Number]], tax_rate: float, fixed_costs: float
) -> None:
    y_gross = y_fees = y_ref = y_net = 0.0
    for b in monthly.values():
        y_gross += b["gross"]
        y_fees += b["fees"]
        y_ref += b["refunds"]
        y_net += b["net"]
    set_aside = y_net * tax_rate
    # fixed costs × number of months present
    months_n = max(len(monthly), 1)
    safe = y_net - set_aside - (fixed_costs * months_n)
    print("=== Seller Ledger Summary (YTD of imported rows) ===")
    print(f"Gross:          ${y_gross:,.2f}")
    print(f"Fees:           ${y_fees:,.2f}")
    print(f"Refunds:        ${y_ref:,.2f}")
    print(f"Net:            ${y_net:,.2f}")
    print(f"Tax set-aside:  ${set_aside:,.2f}  (rate {tax_rate:.0%})")
    print(f"Fixed costs:    ${fixed_costs * months_n:,.2f}  ({fixed_costs:.2f}/mo × {months_n})")
    print(f"Safe-to-spend:  ${safe:,.2f}")
    print("Months:", ", ".join(sorted(monthly.keys())) or "(none)")
    print("NOTE: Estimates only — not tax advice. Verify fees against statements.")


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Gumroad + Stripe seller ledger")
    p.add_argument("--gumroad", type=Path, help="Gumroad payout CSV")
    p.add_argument("--stripe", type=Path, help="Stripe payout/balance CSV")
    p.add_argument("--tax-rate", type=float, default=0.30, help="Effective set-aside rate (default 0.30)")
    p.add_argument("--fixed-costs", type=float, default=0.0, help="Monthly fixed costs to subtract")
    p.add_argument("--out", type=Path, default=Path("out"), help="Output directory")
    args = p.parse_args(argv)

    if not args.gumroad and not args.stripe:
        p.error("Provide --gumroad and/or --stripe CSV path(s)")

    parts = []
    if args.gumroad:
        if not args.gumroad.exists():
            print(f"Missing file: {args.gumroad}", file=sys.stderr)
            return 1
        parts.append(("gumroad", accumulate(load_csv(args.gumroad), "date", "gumroad")))
    if args.stripe:
        if not args.stripe.exists():
            print(f"Missing file: {args.stripe}", file=sys.stderr)
            return 1
        parts.append(
            ("stripe", accumulate(load_csv(args.stripe), "created_date", "stripe"))
        )

    monthly = merge_buckets(*parts)
    out_csv = args.out / "monthly_pnl.csv"
    write_monthly_pnl(out_csv, monthly, args.tax_rate, args.fixed_costs)
    summarize(monthly, args.tax_rate, args.fixed_costs)
    print(f"Wrote {out_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
