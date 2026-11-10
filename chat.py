from bot import answer

def main():
    print("Kettlewise K2 Support. Type 'quit' to exit, 'debug' to toggle details.\n")
    debug = True
    while True:
        q = input("You: ").strip()
        if q.lower() in {"quit", "exit"}:
            break
        if q.lower() == "debug":
            debug = not debug
            print(f"(debug {'on' if debug else 'off'})\n")
            continue
        if not q:
            continue
        r = answer(q)
        print(f"\nBot: {r['answer']}")
        if r["citations"]:
            print("Sources: " + ", ".join(r["citations"]))
        if debug:
            print(f"[refused_by={r['refused_by']}]")
            for h in r["hits"]:
                print(f"   {h['score']:.3f}  {h['id']}")
        print()

if __name__ == "__main__":
    main()
