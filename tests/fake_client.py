"""Offline stand-in for NvidiaClient so the pipeline can be tested without an API key."""
import hashlib
import re

import numpy as np


class FakeClient:
    DIM = 512

    def __init__(self, image_description="Bar chart showing quarterly revenue. Q3 is highest at 42 million."):
        self.image_description = image_description
        self.last_context = ""
        self.last_images = []

    def embed(self, texts, input_type="passage"):
        out = []
        for t in texts:
            v = np.zeros(self.DIM, dtype=np.float32)
            for w in re.findall(r"[a-z0-9]+", t.lower()):
                v[int(hashlib.md5(w.encode()).hexdigest(), 16) % self.DIM] += 1.0
            out.append(v.tolist())
        return out

    def describe_image(self, jpeg: bytes) -> str:
        assert jpeg[:2] == b"\xff\xd8", "expected JPEG bytes"
        return self.image_description

    def answer(self, question, context, images, image_note=""):
        self.last_context, self.last_images = context, images
        return f"fake-answer ({len(images)} image attached)"
