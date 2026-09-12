from sentence_transformers import SentenceTransformer


class EmbeddingService:
    def __init__(self, model_name_or_path: str):
        self.model = SentenceTransformer(
            model_name_or_path=model_name_or_path, device="cpu"
        )

    def embed_documents(
        self, texts: list[str], batch_size: int = 32
    ) -> list[list[float]]:
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=True,
            normalize_embeddings=True,
        )
        return embeddings.tolist()

    def embed_query(self, text: str) -> list[float]:
        embedding = self.model.encode(
            f"Represent this sentence for searching relevant passages: {text}",
            normalize_embeddings=True,
        )
        return embedding.tolist()
