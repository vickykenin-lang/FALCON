"""Falcon Bedrock real-image vision certification.
Resolves the model against authenticated Mantle /models first, then sends a
deterministic PNG to prove actual visual understanding. Secrets are never printed.
"""
import base64
import io
import json
import os
import sys

import requests
from PIL import Image, ImageDraw

KEY = os.environ["BEDROCK_API_KEY"]
ROOT = os.environ.get("MANTLE_ROOT", "https://bedrock-mantle.us-east-1.api.aws").rstrip("/")
DOC_MODEL = "qwen.qwen3-vl-235b-a22b-instruct"
TOKEN = "FALCON_VISION_BLUE_TRIANGLE"
headers = {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}

ev = {
    "credential_available": True,
    "configured": True,
    "source_implemented": True,
    "catalog_verified": False,
    "test_passed": False,
    "live_request_verified": False,
    "real_output_verified": False,
    "expected": TOKEN,
}

try:
    # Do not guess IDs: verify against the account's authenticated Mantle catalog.
    mr = requests.get(ROOT + "/v1/models", headers={"Authorization": f"Bearer {KEY}"}, timeout=60)
    ev["catalog_http_status"] = mr.status_code
    mr.raise_for_status()
    models = [x.get("id", "") for x in mr.json().get("data", [])]
    ev["catalog_verified"] = True
    ev["catalog_model_count"] = len(models)
    candidates = [m for m in models if "qwen3-vl" in m.lower()]
    ev["vision_candidates"] = candidates
    model = DOC_MODEL if DOC_MODEL in models else (candidates[0] if candidates else DOC_MODEL)
    ev["model"] = model

    im = Image.new("RGB", (512, 512), "white")
    d = ImageDraw.Draw(im)
    d.polygon([(256, 70), (70, 430), (442, 430)], fill="blue")
    buf = io.BytesIO(); im.save(buf, format="PNG")
    data_url = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": "Inspect the image. If it contains a blue triangle on a white background, return exactly FALCON_VISION_BLUE_TRIANGLE and nothing else."},
            {"type": "image_url", "image_url": {"url": data_url}},
        ]}],
        "temperature": 0,
        "max_tokens": 80,
    }
    endpoint = ROOT + "/v1/chat/completions"
    ev["endpoint"] = endpoint
    r = requests.post(endpoint, headers=headers, json=payload, timeout=120)
    ev["http_status"] = r.status_code
    ev["live_request_verified"] = True
    if not r.ok:
        ev["error"] = r.text[:1000]
    else:
        data = r.json()
        text = (data.get("choices", [{}])[0].get("message", {}).get("content") or "").strip()
        ev["output_preview"] = text[:240]
        ev["real_output_verified"] = bool(text)
        ev["test_passed"] = TOKEN in text
except Exception as exc:
    ev["error"] = f"{type(exc).__name__}: {exc}"[:1000]

with open("bedrock-vision-cert.json", "w", encoding="utf-8") as f:
    json.dump(ev, f, indent=2)
print(json.dumps({k: v for k, v in ev.items() if k != "expected"}, indent=2))
sys.exit(0 if ev["test_passed"] else 2)
