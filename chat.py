"""Terminal chat.

python chat.py            # the router picks the product for each question
python chat.py phone      # talk to one product's agent only
"""

import sys
import uuid

from bot import answer
from products import PRODUCTS, get_product

HELP = "Commands: 'use <product>', 'use auto', 'products', 'debug', 'quit'."


def main():  # pylint: disable=too-many-branches  # one flat loop of chat commands
    product_id = sys.argv[1] if len(sys.argv) > 1 else None
    if product_id:
        try:
            get_product(product_id)
        except KeyError as e:
            raise SystemExit(e.args[0]) from None
    thread_id = uuid.uuid4().hex  # one conversation, so follow-ups stay with the same product
    debug = True
    print(f"Support chat. Products: {', '.join(PRODUCTS)}. Mode: {product_id or 'auto'}.\n{HELP}\n")

    while True:
        q = input("You: ").strip()
        if q.lower() in {"quit", "exit"}:
            break
        if q.lower() == "debug":
            debug = not debug
            print(f"(debug {'on' if debug else 'off'})\n")
            continue
        if q.lower() == "products":
            for p in PRODUCTS.values():
                print(f"  {p.id}: {p.name}")
            print()
            continue
        if q.lower().startswith("use "):
            choice = q[4:].strip().lower()
            if choice == "auto":
                product_id = None
            elif choice in PRODUCTS:
                product_id = choice
            else:
                print(f"(unknown product; choose from: auto, {', '.join(PRODUCTS)})\n")
                continue
            print(f"(mode: {product_id or 'auto'})\n")
            continue
        if not q:
            continue

        r = answer(q, product_id=product_id, thread_id=thread_id)
        print(f"\nBot [{r['product_name'] or 'no product'}]: {r['answer']}")
        if r["citations"]:
            print("Sources: " + ", ".join(r["citations"]))
        if debug:
            print(f"[source={r['source']} refused_by={r['refused_by']} routed_by={r['routed_by']}]")
            for s in r["trace"]:
                print(f"   -> {s['agent']}: {s['detail']}")
            for h in r["hits"]:
                print(f"   {h['score']:.3f}  {h['id']}")
        print()


if __name__ == "__main__":
    main()
