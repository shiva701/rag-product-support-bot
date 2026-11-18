"""Build the vector index for every product, or only the ones you name.

python ingest.py            # all products
python ingest.py phone      # one product
"""

import sys

from chunker import chunk_documents
from config import MAX_SECTION_CHARS
from embedding import embed_texts
from loader import load_documents
from products import PRODUCTS, get_product
from vector_store import VectorStore


def ingest(product):
    docs = load_documents(str(product.kb_dir))
    chunks = chunk_documents(docs, MAX_SECTION_CHARS)
    if not chunks:
        raise SystemExit(f"{product.kb_dir}: no sections found. Docs need '## ' headings.")
    for c in chunks:
        c["product"] = product.id
    print(f"[{product.id}] {len(docs)} docs -> {len(chunks)} sections")
    for c in chunks:
        print("  ", c["id"])
    vectors = embed_texts([c["text"] for c in chunks])
    VectorStore(vectors, chunks).save(str(product.index_dir))
    print(f"[{product.id}] saved index ({vectors.shape[1]}-dim vectors) to {product.index_dir}/\n")


def main():
    try:
        products = [get_product(a) for a in sys.argv[1:]] or list(PRODUCTS.values())
    except KeyError as e:
        raise SystemExit(e.args[0]) from None
    for product in products:
        ingest(product)


if __name__ == "__main__":
    main()
