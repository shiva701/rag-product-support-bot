import json
from bot import answer

def main():
    tests = json.load(open("eval_set.json"))
    stats = {"retrieval_hit": 0, "retrieval_total": 0,
             "correct_decision": 0, "content_ok": 0, "content_total": 0}

    for t in tests:
        r = answer(t["q"])
        decision_ok = r["found"] == t["should_answer"]
        stats["correct_decision"] += decision_ok
        line = f"{'OK  ' if decision_ok else 'FAIL'} [{'answer' if r['found'] else 'refuse'}] {t['q']}"

        if t["should_answer"]:
            # Retrieval: did the expected section appear in the hits?
            stats["retrieval_total"] += 1
            retrieved = [h["section"] for h in r["hits"]]
            hit = t["expected_section"] in retrieved
            stats["retrieval_hit"] += hit
            # Content: does the answer include the key facts?
            if r["found"]:
                stats["content_total"] += 1
                text = r["answer"].lower()
                missing = [w for w in t["must_include"] if w.lower() not in text]
                stats["content_ok"] += not missing
                if missing:
                    line += f"   (missing: {missing})"
            if not hit:
                line += f"   (retrieval miss; got {retrieved})"
        else:
            if r["found"]:
                line += f"   (should have refused; said: {r['answer'][:80]}...)"
        print(line)

    n = len(tests)
    print("\n=== Scores ===")
    print(f"Answer/refuse decision: {stats['correct_decision']}/{n}")
    print(f"Retrieval hit rate:     {stats['retrieval_hit']}/{stats['retrieval_total']}")
    print(f"Answer content correct: {stats['content_ok']}/{stats['content_total']}")

if __name__ == "__main__":
    main()
