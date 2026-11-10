from config import KB_DIR, INDEX_DIR, MAX_SECTION_CHARS
from loader import load_documents
from chunker import chunk_documents
from embedding import embed_texts
from vector_store import VectorStore

def main():
    docs = load_documents(KB_DIR)
    chunks = chunk_documents(docs, MAX_SECTION_CHARS)
    print(f"{len(docs)} docs -> {len(chunks)} sections")
    for c in chunks:
        print("  ", c["id"])
    vectors = embed_texts([c["text"] for c in chunks])
    VectorStore(vectors, chunks).save(INDEX_DIR)
    print(f"Saved index ({vectors.shape[1]}-dim vectors) to {INDEX_DIR}/")

if __name__ == "__main__":
    main()
