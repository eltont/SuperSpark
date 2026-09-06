#!/usr/bin/env python3
"""Generate deterministic tiny JSONL fixtures and expected result JSON.

Uses pure Python only (stdlib). Seed is fixed at 42 so expected/*.json stay
hand-checkable. Re-run from repo root:

  python3 examples/fixtures/generate_tiny.py
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path

SEED = 42
ROOT = Path(__file__).resolve().parents[1]
TINY = ROOT / "fixtures" / "tiny"
EXPECTED = ROOT / "expected"


def checksum_rows(rows: list[dict]) -> str:
    payload = json.dumps(rows, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")


def write_expected(scenario: str, rows: list[dict], extras: dict | None = None) -> None:
    EXPECTED.mkdir(parents=True, exist_ok=True)
    body = {
        "scenario": scenario,
        "seed": SEED,
        "size": "tiny",
        "row_count": len(rows),
        "checksum": checksum_rows(rows),
        "rows": rows,
    }
    if extras:
        body["extras"] = extras
    path = EXPECTED / f"{scenario}.json"
    path.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"  expected {path.name}: {len(rows)} rows checksum={body['checksum'][:12]}…")


def gen_customers() -> list[dict]:
    tiers = ["gold", "silver", "bronze"]
    countries = ["US", "CA", "UK", "DE"]
    rows = []
    for i in range(1, 11):
        rows.append(
            {
                "customer_id": i,
                "name": f"Customer_{i:02d}",
                "tier": tiers[(i - 1) % 3],
                "country": countries[(i - 1) % 4],
            }
        )
    return rows


def gen_orders() -> list[dict]:
    statuses = ["complete", "pending", "cancelled"]
    regions = ["west", "east", "central", "south"]
    rows = []
    for i in range(1, 41):
        amount = round(10.0 * i + (i % 7) * 3.5, 2)
        rows.append(
            {
                "order_id": i,
                "customer_id": ((i - 1) % 10) + 1,
                "amount": amount,
                "status": statuses[(i - 1) % 3],
                "region": regions[(i - 1) % 4],
                "created_day": 1 + ((i - 1) % 28),
            }
        )
    return rows


def gen_products() -> list[dict]:
    cats = ["books", "electronics", "home", "toys"]
    rows = []
    for i in range(1, 9):
        rows.append(
            {
                "product_id": i,
                "name": f"Product_{i:02d}",
                "category": cats[(i - 1) % 4],
                "price": round(5.0 * i + 0.99, 2),
            }
        )
    return rows


def gen_line_items() -> list[dict]:
    rows = []
    n = 0
    for order_id in range(1, 41):
        for k in range(1, 1 + ((order_id % 3) + 1)):
            n += 1
            product_id = ((order_id + k - 1) % 8) + 1
            qty = 1 + ((order_id + k) % 4)
            unit_price = round(5.0 * product_id + 0.99, 2)
            rows.append(
                {
                    "line_id": n,
                    "order_id": order_id,
                    "product_id": product_id,
                    "qty": qty,
                    "unit_price": unit_price,
                }
            )
    return rows


def gen_text_rows() -> list[dict]:
    samples = [
        "  Hello World  ",
        "spark SQL rocks",
        "Café Münchën",
        "foo-bar-baz",
        "UPPER and lower",
        "123-456-7890",
        "a@b.co",
        "   ",
        "Gluten+Velox",
        "repeat repeat",
    ]
    rows = []
    for i, text in enumerate(samples, start=1):
        rows.append(
            {
                "id": i,
                "text": text,
                "locale": ["en", "de", "fr", "en"][(i - 1) % 4],
            }
        )
    return rows


def gen_skew_events() -> list[dict]:
    """Intentionally skewed key distribution (key=1 dominates)."""
    rows = []
    eid = 0
    # 80 events on key 1, 10 on key 2, 5 on 3, 5 on 4..8
    for key, count in [(1, 80), (2, 10), (3, 5)] + [(k, 1) for k in range(4, 9)]:
        for j in range(count):
            eid += 1
            rows.append(
                {
                    "event_id": eid,
                    "key": key,
                    "value": round((eid * 1.7 + key * 0.3) % 100, 2),
                }
            )
    return rows


def gen_dim_keys() -> list[dict]:
    return [
        {"key": k, "label": f"bucket_{k}", "weight": k * 10}
        for k in range(1, 9)
    ]


def gen_edge_rows() -> list[dict]:
    return [
        {"id": 1, "a": 1.0, "b": 2.0, "s": "ok", "n": 1},
        {"id": 2, "a": None, "b": 2.0, "s": None, "n": None},
        {"id": 3, "a": 0.0, "b": 0.0, "s": "", "n": 0},
        {"id": 4, "a": -1.5, "b": 3.0, "s": "  pad  ", "n": -3},
        {"id": 5, "a": 1e308, "b": 1e308, "s": "unicode-✓", "n": 42},
        {"id": 6, "a": float("nan"), "b": 1.0, "s": "nan-a", "n": 7},
        {"id": 7, "a": 4.0, "b": None, "s": "div0-guard", "n": 2},
        {"id": 8, "a": 2.5, "b": 5.0, "s": "Café", "n": 3},
    ]


def expected_filter_project(orders: list[dict]) -> list[dict]:
    rows = [
        {
            "order_id": o["order_id"],
            "customer_id": o["customer_id"],
            "amount": o["amount"],
            "region": o["region"],
        }
        for o in orders
        if o["amount"] > 50.0 and o["status"] == "complete"
    ]
    return sorted(rows, key=lambda r: r["order_id"])


def expected_joins(orders: list[dict], customers: list[dict]) -> list[dict]:
    cust = {c["customer_id"]: c for c in customers}
    rows = []
    for o in orders:
        c = cust[o["customer_id"]]
        if c["tier"] == "gold" and o["status"] == "complete":
            rows.append(
                {
                    "order_id": o["order_id"],
                    "customer_id": o["customer_id"],
                    "name": c["name"],
                    "country": c["country"],
                    "amount": o["amount"],
                    "region": o["region"],
                }
            )
    return sorted(rows, key=lambda r: r["order_id"])


def expected_aggregate(orders: list[dict]) -> list[dict]:
    buckets: dict[str, list[float]] = {}
    for o in orders:
        if o["status"] != "cancelled":
            buckets.setdefault(o["region"], []).append(o["amount"])
    rows = []
    for region, amounts in buckets.items():
        total = round(sum(amounts), 2)
        cnt = len(amounts)
        avg = round(total / cnt, 4)
        rows.append(
            {
                "region": region,
                "order_count": cnt,
                "amount_sum": total,
                "amount_avg": avg,
            }
        )
    return sorted(rows, key=lambda r: r["region"])


def expected_sort_topk(orders: list[dict], k: int = 10) -> list[dict]:
    ranked = sorted(orders, key=lambda o: (-o["amount"], o["order_id"]))[:k]
    return [
        {
            "order_id": o["order_id"],
            "customer_id": o["customer_id"],
            "amount": o["amount"],
            "status": o["status"],
            "region": o["region"],
        }
        for o in ranked
    ]


def expected_strings(text_rows: list[dict]) -> list[dict]:
    rows = []
    for r in text_rows:
        trimmed = r["text"].strip()
        upper = trimmed.upper()
        lower = trimmed.lower()
        # Spark substring is 1-based; take first 5 chars of trimmed
        sub = trimmed[:5]
        phoneish = re.sub(r"\d", "#", trimmed)
        rows.append(
            {
                "id": r["id"],
                "trimmed": trimmed,
                "upper_text": upper,
                "lower_text": lower,
                "prefix5": sub,
                "digits_masked": phoneish,
                "locale": r["locale"],
            }
        )
    # Keep rows where trimmed length > 0 and lower contains 'a' or 'e'
    filtered = [
        x
        for x in rows
        if len(x["trimmed"]) > 0 and (("a" in x["lower_text"]) or ("e" in x["lower_text"]))
    ]
    return sorted(filtered, key=lambda r: r["id"])


def expected_skew(events: list[dict], dims: list[dict]) -> list[dict]:
    dim = {d["key"]: d for d in dims}
    buckets: dict[int, list[float]] = {}
    for e in events:
        buckets.setdefault(e["key"], []).append(e["value"])
    rows = []
    for key, vals in buckets.items():
        d = dim[key]
        rows.append(
            {
                "key": key,
                "label": d["label"],
                "event_count": len(vals),
                "value_sum": round(sum(vals), 2),
                "weight": d["weight"],
            }
        )
    return sorted(rows, key=lambda r: r["key"])


def expected_parquet_roundtrip(orders: list[dict]) -> list[dict]:
    # Logical checksum of source: count + sum(amount) + min/max order_id
    amounts = [o["amount"] for o in orders]
    return [
        {
            "row_count": len(orders),
            "amount_sum": round(sum(amounts), 2),
            "min_order_id": min(o["order_id"] for o in orders),
            "max_order_id": max(o["order_id"] for o in orders),
        }
    ]


def expected_small_files(orders: list[dict]) -> list[dict]:
    # After writing one file per region then coalescing: same aggregate as region counts
    from collections import Counter

    c = Counter(o["region"] for o in orders)
    rows = [{"region": region, "cnt": cnt} for region, cnt in c.items()]
    return sorted(rows, key=lambda r: r["region"])


def expected_spill(orders: list[dict]) -> list[dict]:
    # Sort by amount desc within region; take top 3 per region (tiny stand-in for spill)
    by_region: dict[str, list[dict]] = {}
    for o in orders:
        by_region.setdefault(o["region"], []).append(o)
    rows = []
    for region, group in by_region.items():
        top = sorted(group, key=lambda o: (-o["amount"], o["order_id"]))[:3]
        for o in top:
            rows.append(
                {
                    "region": region,
                    "order_id": o["order_id"],
                    "amount": o["amount"],
                }
            )
    return sorted(rows, key=lambda r: (r["region"], -r["amount"], r["order_id"]))


def expected_fallback_udf(orders: list[dict]) -> list[dict]:
    def bucket(amount: float) -> str:
        if amount < 100:
            return "low"
        if amount < 300:
            return "mid"
        return "high"

    rows = [
        {
            "order_id": o["order_id"],
            "amount": o["amount"],
            "amount_bucket": bucket(o["amount"]),
        }
        for o in orders
        if o["status"] == "complete"
    ]
    return sorted(rows, key=lambda r: r["order_id"])


def expected_edge_cases(edges: list[dict]) -> list[dict]:
    rows = []
    for e in edges:
        a, b = e["a"], e["b"]
        # Match Spark: null-safe ratio; NaN stays NaN; div by zero -> null via guard
        if a is None or b is None or b == 0:
            ratio = None
        elif isinstance(a, float) and math.isnan(a):
            ratio = float("nan")
        else:
            ratio = round(a / b, 6)
        s = e["s"]
        trimmed = None if s is None else s.strip()
        rows.append(
            {
                "id": e["id"],
                "ratio": ratio,
                "trimmed": trimmed,
                "n_is_null": e["n"] is None,
                "a_is_null": a is None,
            }
        )
    # Drop pure-null ratio with null trimmed for a tighter gold set? Keep all.
    # Normalize NaN for JSON: use null with flag — but Spark collect gives NaN.
    # Store as string "NaN" for JSON portability.
    for r in rows:
        if isinstance(r["ratio"], float) and math.isnan(r["ratio"]):
            r["ratio"] = "NaN"
    return sorted(rows, key=lambda r: r["id"])


def main() -> int:
    print(f"Generating tiny fixtures (seed={SEED}) under {TINY}")
    customers = gen_customers()
    orders = gen_orders()
    products = gen_products()
    line_items = gen_line_items()
    text_rows = gen_text_rows()
    skew_events = gen_skew_events()
    dim_keys = gen_dim_keys()
    edge_rows = gen_edge_rows()

    # JSON-serialize edge rows carefully (NaN -> null with marker in source file)
    edge_for_file = []
    for e in edge_rows:
        row = dict(e)
        if isinstance(row["a"], float) and math.isnan(row["a"]):
            row["a"] = None
            row["a_was_nan"] = True
        else:
            row["a_was_nan"] = False
        edge_for_file.append(row)

    write_jsonl(TINY / "customers.jsonl", customers)
    write_jsonl(TINY / "orders.jsonl", orders)
    write_jsonl(TINY / "products.jsonl", products)
    write_jsonl(TINY / "line_items.jsonl", line_items)
    write_jsonl(TINY / "text_rows.jsonl", text_rows)
    write_jsonl(TINY / "skew_events.jsonl", skew_events)
    write_jsonl(TINY / "dim_keys.jsonl", dim_keys)
    write_jsonl(TINY / "edge_rows.jsonl", edge_for_file)

    meta = {
        "seed": SEED,
        "files": {
            "customers": len(customers),
            "orders": len(orders),
            "products": len(products),
            "line_items": len(line_items),
            "text_rows": len(text_rows),
            "skew_events": len(skew_events),
            "dim_keys": len(dim_keys),
            "edge_rows": len(edge_for_file),
        },
    }
    (TINY / "manifest.json").write_text(
        json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"  wrote fixtures: {meta['files']}")

    print("Computing expected tiny results…")
    write_expected("filter_project", expected_filter_project(orders))
    write_expected("joins", expected_joins(orders, customers))
    write_expected("aggregate", expected_aggregate(orders))
    write_expected("sort_topk", expected_sort_topk(orders, 10))
    write_expected("strings", expected_strings(text_rows))
    write_expected("skew", expected_skew(skew_events, dim_keys))
    write_expected("parquet_roundtrip", expected_parquet_roundtrip(orders))
    write_expected("small_files", expected_small_files(orders))
    write_expected("spill", expected_spill(orders))
    write_expected("fallback_udf", expected_fallback_udf(orders))
    write_expected("edge_cases", expected_edge_cases(edge_rows))
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
