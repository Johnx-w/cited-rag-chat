"""构建镜像时预热本地 MiniLM，避免容器第一次检索才联网下载约 80MB 的模型权重。

没有 EMBEDDING_API_KEY 时，Embedder 会 fail-open 到 Chroma 自带的
DefaultEmbeddingFunction（ONNX MiniLM），权重默认缓存在
~/.cache/chroma/onnx_models。这里提前触发一次下载并写进镜像层。

刻意不让失败中断构建：运行时仍会自行下载，只是首次问答会慢十几秒。
"""

from __future__ import annotations

import pathlib
import traceback

CACHE = pathlib.Path.home() / ".cache" / "chroma"


def main() -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    try:
        from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

        DefaultEmbeddingFunction()(["warm up"])
        print("[warmup] MiniLM baked into the image")
    except Exception:  # noqa: BLE001
        print("[warmup] skipped, runtime will download on first use")
        traceback.print_exc()


if __name__ == "__main__":
    main()
