"""Suggest a min_score (retrieval refusal gate) for each product from its eval set.

    python calibrate.py            # all products
    python calibrate.py resume     # one product

Put the suggested value in kb/<product>/product.toml as min_score.
"""

import json
import sys

from products import PRODUCTS, get_product
from rag import retrieve


def calibrate(product):
    if not product.eval_path.exists():
        print(f"[{product.id}] no {product.eval_path}, skipped\n")
        return
    tests = json.loads(product.eval_path.read_text())

    # Answerable = the docs have the answer. General-knowledge questions count as unanswerable
    # here because retrieval should NOT find a good match for them.
    def in_docs(t):
        return t["should_answer"] and t.get("expected_source", "docs") == "docs"

    def best(q):
        return retrieve(q, product, k=1)[0]["score"]

    a = sorted(best(t["q"]) for t in tests if in_docs(t))
    u = sorted(best(t["q"]) for t in tests if not in_docs(t))

    print(f"[{product.id}] current min_score = {product.min_score}")
    print("  In the docs, best scores:    ", [f"{s:.3f}" for s in a])
    print("  Not in the docs, best scores:", [f"{s:.3f}" for s in u])
    print(f"  Lowest in-docs score:      {a[0]:.3f}")
    print(f"  Highest not-in-docs score: {u[-1]:.3f}")
    if a[0] > u[-1]:
        print(f"  Suggested min_score ≈ {(a[0] + u[-1]) / 2:.2f} (midpoint)\n")
    else:
        print(
            f"  The two groups overlap. Keep min_score below {a[0]:.2f} and let the model "
            "handle borderline questions.\n"
        )


def main():
    try:
        products = [get_product(a) for a in sys.argv[1:]] or list(PRODUCTS.values())
    except KeyError as e:
        raise SystemExit(e.args[0]) from None
    for product in products:
        calibrate(product)


if __name__ == "__main__":
    main()
