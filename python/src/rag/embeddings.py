"""OpenAI-compatible embedding client with local fail-open."""

from __future__ import annotations

from openai import OpenAI

from src.config import Settings, get_settings


class Embedder:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.client: OpenAI | None = None
        self.model = self.settings.embedding_model
        self._local = None
        key = self.settings.resolved_embedding_key()
        if key:
            kwargs: dict = {"api_key": key}
            base = self.settings.resolved_embedding_base_url()
            if base:
                kwargs["base_url"] = base
            self.client = OpenAI(**kwargs)

    def _local_fn(self):
        if self._local is None:
            from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

            self._local = DefaultEmbeddingFunction()
        return self._local

    def _embed_local(self, texts: list[str]) -> list[list[float]]:
        vectors = self._local_fn()(texts)
        return [list(map(float, row)) for row in vectors]

    def _embed_api(self, texts: list[str], batch_size: int) -> list[list[float]]:
        if self.client is None:
            raise RuntimeError("no embedding client")
        vectors: list[list[float]] = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            resp = self.client.embeddings.create(model=self.model, input=batch)
            ordered = sorted(resp.data, key=lambda x: x.index)
            vectors.extend([list(item.embedding) for item in ordered])
        return vectors

    def embed_documents(self, texts: list[str], batch_size: int = 16) -> list[list[float]]:
        if not texts:
            return []
        if self.client is not None:
            try:
                return self._embed_api(texts, batch_size)
            except Exception as exc:  # noqa: BLE001
                print(f"[embed] API failed, local MiniLM fallback: {exc}")
        return self._embed_local(texts)

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]
