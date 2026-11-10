import json
from pathlib import Path
import numpy as np

class VectorStore:
    def __init__(self, vectors: np.ndarray, chunks: list[dict]):
        self.vectors = vectors
        self.chunks = chunks

    def search(self, query_vec: np.ndarray, k: int) -> list[dict]:
        scores = self.vectors @ query_vec
        top = np.argsort(-scores)[:k]
        return [{**self.chunks[i], "score": float(scores[i])} for i in top]

    def save(self, folder: str):
        Path(folder).mkdir(parents=True, exist_ok=True)
        np.save(Path(folder) / "vectors.npy", self.vectors)
        (Path(folder) / "chunks.json").write_text(json.dumps(self.chunks, indent=2))

    @classmethod
    def load(cls, folder: str) -> "VectorStore":
        return cls(np.load(Path(folder) / "vectors.npy"),
                   json.loads((Path(folder) / "chunks.json").read_text()))
