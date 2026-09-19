#!/usr/bin/env python3
"""
Payout / fee audit helper for sellers.

Compares expected platform+processor fees vs actual net on a unified ledger
or raw Gumroad/Stripe CSVs. Flags rows where fee % looks abnormal.

Usage:
  python3 payout_fee_audit.py --ledger /tmp/unified_ledger.csv
  python3 payout_fee_audit.py --gumroad ../samples/sample_gumroad_sales.csv \\
      --stripe ../samples/sample_stripe_balance.csv --category-map ../schemas/category_map.csv
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import List, Optional

# Reuse P&L normalizer
sys.path.insert(0, str(Path(__file__).resolve().parent))
from seller_ledger_pnl import (  # noqa: E402
    from_gumroad,
    from_stripe,
    load_category_map,
    load_csv,
    money,
)


def audit_rows(rows, low: float = 0.02, high: float = 0.20) -> None:
    print(f"{'id':<12} {'source':<8} {'gross':>10} {'fees':>10} {'fee%':>8} {'net':>10}  flag")
    flagged = 0
    for r in rows:
        if r.category in ("payouts", "fees_only", "refunds_adjustments"):
            continue
        if r.gross <= 0:
            continue
        fees = r.platform_fee + r.processor_fee
        pct = fees / r.gross if r.gross else 0.0
        flag = ""
        if pct < low:
            flag = "LOW_FEE"
        elif pct > high:
            flag = "HIGH_FEE"
        if abs(r.net - (r.gross - fees - r.refunds)) > 0.05 and r.chargebacks == 0:
            flag = (flag + "+NET_MISMATCH").strip("+")
        if flag:
            flagged += 1
        print(
            f"{r.ledger_id:<12} {r.source:<8} {r.gross:10.2f} {fees:10.2f} {pct:7.1%} {r.net:10.2f}  {flag}"
        )
    print(f"\nFlagged rows: {flagged} (thresholds fee% outside {low:.0%}–{high:.0%} or net mismatch)")
    print("Disclaimer: Heuristic only — Gumroad/Stripe fee schedules vary by plan and country.")


def from_ledger_csv(path: Path):
    from seller_ledger_pnl import LedgerRow

    rows = []
    with path.open(newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            rows.append(
                LedgerRow(
                    ledger_id=r.get("ledger_id", ""),
                    source=r.get("source", ""),
                    source_txn_id=r.get("source_txn_id", ""),
                    txn_date=r.get("txn_date", ""),
                    product_or_desc=r.get("product_or_desc", ""),
                    category=r.get("category", ""),
                    gross=money(r.get("gross", "0")),
                    platform_fee=money(r.get("platform_fee", "0")),
                    processor_fee=money(r.get("processor_fee", "0")),
                    refunds=money(r.get("refunds", "0")),
                    chargebacks=money(r.get("chargebacks", "0")),
                    tax_collected=money(r.get("tax_collected", "0")),
                    net=money(r.get("net", "0")),
                    currency=r.get("currency", "usd"),
                    month=r.get("month", ""),
                    quarter=r.get("quarter", ""),
                    year=r.get("year", ""),
                )
            )
    return rows


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Audit seller fee % on Gumroad/Stripe rows")
    p.add_argument("--ledger", type=Path, help="Unified ledger CSV from seller_ledger_pnl.py")
    p.add_argument("--gumroad", type=Path)
    p.add_argument("--stripe", type=Path)
    p.add_argument("--category-map", type=Path)
    p.add_argument("--low", type=float, default=0.02)
    p.add_argument("--high", type=float, default=0.20)
    args = p.parse_args(argv)

    if args.ledger:
        rows = from_ledger_csv(args.ledger)
    else:
        if not args.gumroad and not args.stripe:
            p.error("Provide --ledger or --gumroad/--stripe")
        rules = load_category_map(args.category_map)
        rows = []
        if args.gumroad:
            rows.extend(from_gumroad(load_csv(args.gumroad), rules))
        if args.stripe:
            rows.extend(from_stripe(load_csv(args.stripe), rules))
    audit_rows(rows, args.low, args.high)
    return 0


if __name__ == "__main__":
    sys.exit(main())
