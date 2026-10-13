"""NVIDIA NIM client (OpenAI-compatible): embeddings + vision-language model."""
import base64
import time

from openai import OpenAI

from . import config

DESCRIBE_PROMPT = (
    "You are indexing a document image so it can be found by search later.\n"
    "1) TRANSCRIPT: transcribe ALL visible text exactly as written (keep table rows/columns, numbers, units, headings).\n"
    "2) VISUAL: describe what is shown: charts (type, axes, key values and trends), diagrams (components and links), "
    "photos (objects, scene), screenshots (UI elements), handwriting.\n"
    "Be factual and complete. Do not invent anything that is not visible."
)

ANSWER_SYSTEM = (
    "You answer questions about the user's documents. Use ONLY the provided context blocks (and the attached image, if any). "
    "Context blocks are numbered like [1], [2]; cite the ones you used, e.g. [1][3]. "
    "Some blocks are text from the document, others are descriptions/transcripts of images from the document. "
    "If the answer is not in the context, say you could not find it in the documents. Do not guess."
)


class NvidiaClient:
    def __init__(self, api_key=None, base_url=None, embed_model=None, vlm_model=None):
        key = api_key or config.NVIDIA_API_KEY
        if not key:
            raise RuntimeError("NVIDIA_API_KEY is not set. Copy .env.example to .env and add your key.")
        self.client = OpenAI(api_key=key, base_url=base_url or config.BASE_URL)
        self.embed_model = embed_model or config.EMBED_MODEL
        self.vlm_model = vlm_model or config.VLM_MODEL

    @staticmethod
    def _retry(fn, tries: int = 3):
        for i in range(tries):
            try:
                return fn()
            except Exception:
                if i == tries - 1:
                    raise
                time.sleep(2 ** i)

    def embed(self, texts: list[str], input_type: str = "passage") -> list[list[float]]:
        """input_type: 'passage' for documents, 'query' for questions (nv-embedqa models need this)."""
        out: list[list[float]] = []
        for i in range(0, len(texts), 32):
            batch = texts[i:i + 32]
            resp = self._retry(lambda: self.client.embeddings.create(
                model=self.embed_model,
                input=batch,
                encoding_format="float",
                extra_body={"input_type": input_type, "truncate": "END"},
            ))
            out.extend(d.embedding for d in resp.data)
        return out

    @staticmethod
    def _data_url(jpeg: bytes) -> str:
        return "data:image/jpeg;base64," + base64.b64encode(jpeg).decode()

    def describe_image(self, jpeg: bytes) -> str:
        messages = [{"role": "user", "content": [
            {"type": "text", "text": DESCRIBE_PROMPT},
            {"type": "image_url", "image_url": {"url": self._data_url(jpeg)}},
        ]}]
        resp = self._retry(lambda: self.client.chat.completions.create(
            model=self.vlm_model, messages=messages, max_tokens=1024, temperature=0.1))
        return (resp.choices[0].message.content or "").strip()

    def answer(self, question: str, context: str, images: list[bytes], image_note: str = "") -> str:
        content = [{"type": "text", "text": f"Context:\n{context}\n\n{image_note}\nQuestion: {question}"}]
        for img in images:
            content.append({"type": "image_url", "image_url": {"url": self._data_url(img)}})
        messages = [{"role": "system", "content": ANSWER_SYSTEM}, {"role": "user", "content": content}]
        resp = self._retry(lambda: self.client.chat.completions.create(
            model=self.vlm_model, messages=messages, max_tokens=1024, temperature=0.2))
        return (resp.choices[0].message.content or "").strip()
