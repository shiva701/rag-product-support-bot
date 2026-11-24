"""Grade each product's agent against kb/<product>/eval_set.json, then grade the router.

python evaluate.py                  # all products
python evaluate.py phone            # one product
python evaluate.py --judge phone    # also have JUDGE_MODEL grade each answer (slower)
"""

import argparse
import json

from bot import answer
from config import JUDGE_MODEL
from judge import judge_docs, judge_general
from products import PRODUCTS, get_product
from rag import pick_product


def evaluate(product, use_judge: bool = False) -> list[dict]:
    """Ask every question straight to this product's agent. Returns the test list."""
    tests = json.loads(product.eval_path.read_text())
    stats = {
        "decision": 0,
        "retrieval_hit": 0,
        "retrieval_total": 0,
        "content_ok": 0,
        "content_total": 0,
        "judged": 0,  # answers the judge graded
        "judge_pass": 0,
        "judge_failed_to_grade": 0,
        "faithfulness": 0,  # sums of docs-answer scores, for averages
        "completeness": 0,
        "docs_judged": 0,
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
        if use_judge and r["source"] in ("docs", "general"):
            line += run_judge(t, r, product, stats)
        print(line)

    print(f"\nDecision (docs / general / refuse): {stats['decision']}/{len(tests)}")
    print(
        f"Retrieval hit rate:                 {stats['retrieval_hit']}/{stats['retrieval_total']}"
    )
    print(f"Answer content correct:             {stats['content_ok']}/{stats['content_total']}")
    if use_judge:
        label = f"Judge pass ({JUDGE_MODEL}):"
        print(f"{label:<36}{stats['judge_pass']}/{stats['judged']}")
        if stats["docs_judged"]:
            n = stats["docs_judged"]
            print(
                f"  avg faithfulness / completeness:  "
                f"{stats['faithfulness'] / n:.2f} / {stats['completeness'] / n:.2f}  (1-5)"
            )
        if stats["judge_failed_to_grade"]:
            print(f"  judge reply unusable:             {stats['judge_failed_to_grade']}")
    print()
    return tests


def run_judge(t: dict, r: dict, product, stats: dict) -> str:
    """Have the judge model grade one answer. Returns text to add to the result line."""
    if r["source"] == "docs":
        j = judge_docs(t["q"], r["answer"], r["hits"], t.get("reference"))
    else:
        j = judge_general(t["q"], r["answer"], product)
    if not j:
        stats["judge_failed_to_grade"] += 1
        return "   (judge: reply unusable)"

    stats["judged"] += 1
    stats["judge_pass"] += j["passed"]
    if r["source"] == "docs":
        stats["docs_judged"] += 1
        stats["faithfulness"] += j["faithfulness"]
        stats["completeness"] += j["completeness"]
        scores = f"faith {j['faithfulness']}, complete {j['completeness']}"
        if "correctness" in j:
            scores += f", correct {j['correctness']}"
    else:
        scores = f"leaks facts {j['leaks_product_facts']}, helpful {j['helpfulness']}"
    if j["passed"]:
        return f"   (judge OK: {scores})"
    detail = f"   (judge FAIL: {scores}; {j['reasoning'][:200]}"
    if j.get("unsupported_claims"):
        detail += f"; unsupported: {j['unsupported_claims']}"
    return detail + ")"


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
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("products", nargs="*", help="product ids (default: all)")
    parser.add_argument(
        "--judge", action="store_true", help=f"also grade answers with {JUDGE_MODEL}"
    )
    args = parser.parse_args()
    try:
        products = [get_product(a) for a in args.products] or list(PRODUCTS.values())
    except KeyError as e:
        raise SystemExit(e.args[0]) from None
    tests_by_product = {p.id: evaluate(p, args.judge) for p in products if p.eval_path.exists()}
    if len(PRODUCTS) > 1:
        evaluate_router(tests_by_product)


if __name__ == "__main__":
    main()
