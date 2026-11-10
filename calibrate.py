from bot import retrieve

ANSWERABLE = [
    "How do I descale the kettle?",
    "What does error E3 mean?",
    "How long is the warranty?",
    "Can I schedule the kettle?",
    "Is it BPA-free?",
    "How do I turn on keep warm?",
]
UNANSWERABLE = [
    "How much does it cost?",
    "Does it come in red?",
    "What's the capital of France?",
    "How do I reset my router?",
    "Is there a 220 V version?",
    "Recommend a good tea.",
]

def best_score(q):
    return retrieve(q, k=1)[0]["score"]

a = sorted(best_score(q) for q in ANSWERABLE)
u = sorted(best_score(q) for q in UNANSWERABLE)
print("Answerable best scores:  ", [f"{s:.3f}" for s in a])
print("Unanswerable best scores:", [f"{s:.3f}" for s in u])
print(f"\nLowest answerable:    {a[0]:.3f}")
print(f"Highest unanswerable: {u[-1]:.3f}")
print(f"Suggested MIN_SCORE ≈ {(a[0] + u[-1]) / 2:.3f} (midpoint)")
