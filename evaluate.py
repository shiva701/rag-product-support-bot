"""Grade each product's agent against kb/<product>/eval_set.json, then grade the router.

python evaluate.py            # all products
python evaluate.py phone      # one product
"""

import json
import sys

from bot import answer
from products import PRODUCTS, get_product
from rag import pick_product


def evaluate(product) -> list[dict]:
    """Ask every question straight to this product's agent. Returns the test list."""
    tests = json.loads(product.eval_path.read_text())
    stats = {
        "decision": 0,
        "retrieval_hit": 0,
        "retrieval_total": 0,
        "content_ok": 0,
        "content_total": 0,
    }
    print(f"=== {product.name} ({product.id}) ===")

    for t in tests:
        r = answer(t["q"], product_id=product.id)
        # "source" is "docs", "general", or None (refused). Default expectation: docs.
        expected_source = t.get("expected_source", "docs") if t["should_answer"] else None
        decision_ok = r["source"] == expected_source
        stats["decision"] += decision_ok
        line = f"{'OK  ' if decision_ok else 'FAIL'} [{r['source'] or 'refuse'}] {t['q']}"
        if not decision_ok:
            line += f"   (expected {expected_source or 'refuse'}; said: {r['answer'][:80]}...)"

        if expected_source == "docs":
            # Retrieval: did the expected section appear in the hits?
            stats["retrieval_total"] += 1
            retrieved = [h["section"] for h in r["hits"]]
            hit = t["expected_section"] in retrieved
            stats["retrieval_hit"] += hit
            if not hit:
                line += f"   (retrieval miss; got {retrieved})"
            # Content: does the answer include the key facts?
            if r["source"] == "docs":
                stats["content_total"] += 1
                text = r["answer"].lower()
                missing = [w for w in t["must_include"] if w.lower() not in text]
                stats["content_ok"] += not missing
                if missing:
                    line += f"   (missing: {missing})"
        print(line)

    print(f"\nDecision (docs / general / refuse): {stats['decision']}/{len(tests)}")
    print(
        f"Retrieval hit rate:                 {stats['retrieval_hit']}/{stats['retrieval_total']}"
    )
    print(f"Answer content correct:             {stats['content_ok']}/{stats['content_total']}\n")
    return tests


def evaluate_router(tests_by_product: dict[str, list[dict]]):
    """Without telling the router the product, does it send each question to the right agent?"""
    print("=== Router ===")
    ok = total = 0
    for product_id, tests in tests_by_product.items():
        for t in tests:
            if not t["should_answer"]:
                continue  # out-of-scope questions have no right product
            total += 1
            picked = pick_product(t["q"])
            # "ambiguous": the question alone doesn't say which product (e.g. "How long is
            # the warranty?"). Asking the user (none) is fine; a different product is not.
            good = picked == product_id or (picked is None and t.get("ambiguous", False))
            ok += good
            if not good:
                print(f"FAIL expected {product_id}, got {picked or 'none'}: {t['q']}")
    print(f"Routing accuracy: {ok}/{total}\n")


def main():
    try:
        products = [get_product(a) for a in sys.argv[1:]] or list(PRODUCTS.values())
    except KeyError as e:
        raise SystemExit(e.args[0]) from None
    tests_by_product = {p.id: evaluate(p) for p in products if p.eval_path.exists()}
    if len(PRODUCTS) > 1:
        evaluate_router(tests_by_product)


if __name__ == "__main__":
    main()
