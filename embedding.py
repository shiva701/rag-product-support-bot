import numpy as np
from sentence_transformers import SentenceTransformer
from config import EMBED_MODEL

_model = SentenceTransformer(EMBED_MODEL)

def embed_texts(texts: list[str], batch_size: int = 64) -> np.ndarray:
    # normalize_embeddings=True -> unit length, so dot product = cosine similarity
    return _model.encode(texts, batch_size=batch_size, normalize_embeddings=True,
                         convert_to_numpy=True).astype(np.float32)
