#!/usr/bin/env python3
"""
Gumroad + Stripe Seller Ledger — fee-aware P&L calculator.

Reads Gumroad sales CSV and/or Stripe balance-transaction CSV, normalizes rows,
applies category map, and prints monthly / YTD / quarterly summaries.

NOT tax advice. Offline / file-based only — no API keys.

Usage:
  python3 seller_ledger_pnl.py \\
    --gumroad ../samples/sample_gumroad_sales.csv \\
    --stripe ../samples/sample_stripe_balance.csv \\
    --category-map ../schemas/category_map.csv \\
    --tax-rate 0.30 \\
    --write-ledger /tmp/unified_ledger.csv
"""
from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple


def money(s: str) -> float:
    s = (s or "").replace("$", "").replace(",", "").strip()
    if not s:
        return 0.0
    return round(float(s), 2)


def cents_to_dollars(s: str) -> float:
    s = (s or "").strip()
    if not s:
        return 0.0
    # If value looks like dollars already (has decimal), treat as dollars
    if "." in s:
        return money(s)
    return round(int(float(s)) / 100.0, 2)


def parse_date(s: str) -> str:
    s = (s or "").strip()
    if not s:
        return ""
    # Take date portion if datetime
    s = s.split(" ")[0].split("T")[0]
    if "/" in s:
        parts = s.split("/")
        if len(parts) == 3:
            m, d, y = parts
            if len(y) == 2:
                y = "20" + y
            return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"
    return s


def ym_q(date: str) -> Tuple[str, str, str]:
    if len(date) < 7:
        return "", "", ""
    y, m = date[:4], date[5:7]
    q = f"Q{(int(m) - 1) // 3 + 1}"
    return y, f"{y}-{m}", f"{y}-{q}"


def load_csv(path: Path) -> List[dict]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        rows = []
        for row in csv.DictReader(f):
            # skip comment-only / empty
            if not any((v or "").strip() for v in row.values()):
                continue
            rows.append(row)
        return rows


def load_category_map(path: Optional[Path]) -> List[Tuple[str, str]]:
    if not path or not path.exists():
        return [("*", "other")]
    rules: List[Tuple[str, str]] = []
    with path.open(newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            pat = (row.get("pattern") or "").strip()
            cat = (row.get("category") or "other").strip()
            if not pat or pat.startswith("#"):
                continue
            rules.append((pat.lower(), cat))
    if not any(p == "*" for p, _ in rules):
        rules.append(("*", "other"))
    return rules


def categorize(text: str, rules: List[Tuple[str, str]]) -> str:
    t = (text or "").lower()
    for pat, cat in rules:
        if pat == "*":
            return cat
        if pat in t:
            return cat
    return "other"


@dataclass
class LedgerRow:
    ledger_id: str
    source: str
    source_txn_id: str
    txn_date: str
    product_or_desc: str
    category: str
    gross: float
    platform_fee: float
    processor_fee: float
    refunds: float
    chargebacks: float
    tax_collected: float
    net: float
    currency: str
    month: str
    quarter: str
    year: str


def from_gumroad(rows: List[dict], rules: List[Tuple[str, str]]) -> List[LedgerRow]:
    out: List[LedgerRow] = []
    for i, r in enumerate(rows, 1):
        # Skip schema comment files that somehow got parsed with wrong headers
        if "sale_id" not in {k.lower() for k in r.keys()} and "sale_id" not in r:
            # try flexible
            pass
        sid = (r.get("sale_id") or r.get("id") or f"gum-{i}").strip()
        date = parse_date(r.get("sale_date") or r.get("date") or r.get("created_at") or "")
        product = (r.get("product_name") or r.get("product") or "").strip()
        sale_type = (r.get("sale_type") or "").strip()
        label = f"{product} {sale_type}".strip()
        gross = cents_to_dollars(r.get("price_cents") or r.get("price") or "0")
        fee = cents_to_dollars(r.get("gumroad_fee_cents") or r.get("fee_cents") or "0")
        tax = cents_to_dollars(r.get("tax_cents") or "0")
        refunded = cents_to_dollars(r.get("amount_refunded_cents") or "0")
        net = cents_to_dollars(r.get("net_cents") or "0")
        if not net and gross:
            net = round(gross - fee - refunded, 2)
        chargeback = 0.0
        if str(r.get("chargebacked") or "").lower() in ("true", "1", "yes"):
            chargeback = net if net else gross
            net = 0.0
        y, month, quarter = ym_q(date)
        cat = categorize(label, rules)
        if str(r.get("refunded") or "").lower() in ("true", "1", "yes") or refunded > 0:
            if cat == "other":
                cat = "refunds_adjustments"
        out.append(
            LedgerRow(
                ledger_id=f"GUM-{i:04d}",
                source="gumroad",
                source_txn_id=sid,
                txn_date=date,
                product_or_desc=product or sale_type or sid,
                category=cat,
                gross=gross,
                platform_fee=fee,
                processor_fee=0.0,
                refunds=refunded,
                chargebacks=chargeback,
                tax_collected=tax,
                net=net,
                currency=(r.get("currency") or "usd").lower(),
                month=month,
                quarter=quarter,
                year=y,
            )
        )
    return out


def from_stripe(rows: List[dict], rules: List[Tuple[str, str]]) -> List[LedgerRow]:
    out: List[LedgerRow] = []
    for i, r in enumerate(rows, 1):
        # Flexible column names
        lower = {k.lower().strip(): v for k, v in r.items()}

        def g(*names: str) -> str:
            for n in names:
                if n.lower() in lower:
                    return lower[n.lower()] or ""
            return ""

        tid = g("id", "balance_transaction_id", "txn_id") or f"stripe-{i}"
        date = parse_date(g("created (utc)", "created", "date", "available on (utc)"))
        desc = g("description", "desc", "name")
        typ = g("type", "reporting_category", "reporting category")
        amount = money(g("amount", "customer_facing_amount"))
        fee = money(g("fee", "stripe_fee"))
        net = money(g("net"))
        if not net and amount:
            net = round(amount - fee, 2)
        # Classify refunds / chargebacks / payouts
        refunds = 0.0
        chargebacks = 0.0
        processor_fee = fee
        platform_fee = 0.0
        gross = amount if amount > 0 else 0.0
        typ_l = typ.lower()
        desc_l = desc.lower()
        if typ_l in ("refund",) or "refund" in desc_l:
            refunds = abs(amount) if amount < 0 else abs(money(g("amount")))
            gross = 0.0
            net = -refunds if net >= 0 and amount < 0 else net
        if typ_l in ("adjustment", "dispute") or "chargeback" in desc_l or "dispute" in desc_l:
            chargebacks = abs(amount) if amount < 0 else abs(amount)
            if amount < 0:
                gross = 0.0
        if typ_l == "payout" or "payout" in desc_l:
            # Informational — money leaving Stripe to bank; exclude from P&L net
            cat = "payouts"
            out.append(
                LedgerRow(
                    ledger_id=f"STR-{i:04d}",
                    source="stripe",
                    source_txn_id=tid,
                    txn_date=date,
                    product_or_desc=desc or typ,
                    category=cat,
                    gross=0.0,
                    platform_fee=0.0,
                    processor_fee=0.0,
                    refunds=0.0,
                    chargebacks=0.0,
                    tax_collected=0.0,
                    net=amount,  # negative payout amount kept for cash-movement view
                    currency=g("currency") or "usd",
                    month=ym_q(date)[1],
                    quarter=ym_q(date)[2],
                    year=ym_q(date)[0],
                )
            )
            continue
        if typ_l in ("stripe_fee", "fee") or "fee" in typ_l:
            cat = "fees_only"
            processor_fee = abs(amount) if fee == 0 else fee
            gross = 0.0
        else:
            cat = categorize(f"{desc} {typ}", rules)
        y, month, quarter = ym_q(date)
        out.append(
            LedgerRow(
                ledger_id=f"STR-{i:04d}",
                source="stripe",
                source_txn_id=tid,
                txn_date=date,
                product_or_desc=desc or typ or tid,
                category=cat,
                gross=gross,
                platform_fee=platform_fee,
                processor_fee=processor_fee,
                refunds=refunds,
                chargebacks=chargebacks,
                tax_collected=0.0,
                net=net,
                currency=(g("currency") or "usd").lower(),
                month=month,
                quarter=quarter,
                year=y,
            )
        )
    return out


def summarize(rows: List[LedgerRow], tax_rate: float) -> None:
    # Exclude payouts from P&L aggregates
    pnl = [r for r in rows if r.category != "payouts"]
    by_month: Dict[str, dict] = defaultdict(lambda: defaultdict(float))
    by_cat: Dict[str, dict] = defaultdict(lambda: defaultdict(float))
    by_q: Dict[str, dict] = defaultdict(lambda: defaultdict(float))

    def acc(bucket, key, r: LedgerRow):
        bucket[key]["gross"] += r.gross
        bucket[key]["platform_fee"] += r.platform_fee
        bucket[key]["processor_fee"] += r.processor_fee
        bucket[key]["refunds"] += r.refunds
        bucket[key]["chargebacks"] += r.chargebacks
        bucket[key]["net"] += r.net

    for r in pnl:
        if r.month:
            acc(by_month, r.month, r)
        if r.quarter:
            acc(by_q, r.quarter, r)
        acc(by_cat, r.category, r)

    def print_table(title: str, bucket: Dict[str, dict]):
        print(f"\n=== {title} ===")
        print(f"{'key':<18} {'gross':>10} {'plat_fee':>10} {'proc_fee':>10} {'refunds':>10} {'chgbk':>10} {'net':>10}")
        totals = defaultdict(float)
        for k in sorted(bucket.keys()):
            b = bucket[k]
            print(
                f"{k:<18} {b['gross']:10.2f} {b['platform_fee']:10.2f} {b['processor_fee']:10.2f} "
                f"{b['refunds']:10.2f} {b['chargebacks']:10.2f} {b['net']:10.2f}"
            )
            for f in ("gross", "platform_fee", "processor_fee", "refunds", "chargebacks", "net"):
                totals[f] += b[f]
        print(
            f"{'TOTAL':<18} {totals['gross']:10.2f} {totals['platform_fee']:10.2f} {totals['processor_fee']:10.2f} "
            f"{totals['refunds']:10.2f} {totals['chargebacks']:10.2f} {totals['net']:10.2f}"
        )
        return totals

    print_table("Monthly P&L (ex-payouts)", by_month)
    print_table("Quarterly P&L", by_q)
    print_table("By category", by_cat)

    ytd_net = sum(r.net for r in pnl)
    fees = sum(r.platform_fee + r.processor_fee for r in pnl)
    tax_set_aside = round(max(0.0, ytd_net) * tax_rate, 2)
    safe = round(ytd_net - tax_set_aside, 2)
    print("\n=== YTD snapshot ===")
    print(f"  Rows (ex-payouts): {len(pnl)}")
    print(f"  Gross:             {sum(r.gross for r in pnl):.2f}")
    print(f"  Fees (all):        {fees:.2f}")
    print(f"  Refunds:           {sum(r.refunds for r in pnl):.2f}")
    print(f"  Chargebacks:       {sum(r.chargebacks for r in pnl):.2f}")
    print(f"  Net:               {ytd_net:.2f}")
    print(f"  Tax set-aside @{tax_rate:.0%}: {tax_set_aside:.2f}  (planning only — not tax advice)")
    print(f"  Safe-to-spend:     {safe:.2f}  (net − tax set-aside; excludes fixed costs)")
    print("\nDisclaimer: Educational planning tool only. Confirm with a CPA.")


def write_ledger(path: Path, rows: List[LedgerRow]) -> None:
    fields = list(asdict(rows[0]).keys()) if rows else [
        "ledger_id", "source", "source_txn_id", "txn_date", "product_or_desc", "category",
        "gross", "platform_fee", "processor_fee", "refunds", "chargebacks", "tax_collected",
        "net", "currency", "month", "quarter", "year",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow(asdict(r))
    print(f"\nWrote unified ledger → {path} ({len(rows)} rows)")


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Gumroad + Stripe seller fee-aware P&L")
    p.add_argument("--gumroad", type=Path, help="Gumroad sales CSV")
    p.add_argument("--stripe", type=Path, help="Stripe balance transactions CSV")
    p.add_argument("--category-map", type=Path, default=None, help="category_map.csv")
    p.add_argument("--tax-rate", type=float, default=0.30, help="Planning tax set-aside rate (default 0.30)")
    p.add_argument("--write-ledger", type=Path, default=None, help="Write unified ledger CSV")
    args = p.parse_args(argv)

    if not args.gumroad and not args.stripe:
        p.error("Provide --gumroad and/or --stripe")

    rules = load_category_map(args.category_map)
    rows: List[LedgerRow] = []
    if args.gumroad:
        rows.extend(from_gumroad(load_csv(args.gumroad), rules))
    if args.stripe:
        rows.extend(from_stripe(load_csv(args.stripe), rules))
    rows.sort(key=lambda r: (r.txn_date, r.ledger_id))

    summarize(rows, args.tax_rate)
    if args.write_ledger:
        write_ledger(args.write_ledger, rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
