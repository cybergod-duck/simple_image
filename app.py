import os
import uuid
import base64
import requests
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev")

# ---- ENV VARS ----
REPLICATE_API_KEY = os.getenv("REPLICATE_API_KEY")
RUNPOD_API_KEY = os.getenv("RUNPOD_API_KEY")
RUNPOD_ENDPOINT_ID = os.getenv("RUNPOD_ENDPOINT_ID")
A1111URL = os.getenv("A1111URL", "")

# ---- HOME PAGE ----
@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

# ---- PROMPT ENHANCER (REPLICATE) ----
MODEL = "spuuntries/hermes-2-pro-mistral-7b"
MODEL_URL = f"https://api.replicate.com/v1/models/{MODEL}/predictions"

@app.route("/enhance", methods=["POST"])
def enhance():
    data = request.get_json()
    user_prompt = (data or {}).get("prompt", "").strip()

    if not user_prompt:
        return jsonify({"error": "No prompt provided"}), 400

    try:
        r = requests.post(
            MODEL_URL,
            headers={
                "Authorization": f"Bearer {REPLICATE_API_KEY}",
                "Content-Type": "application/json",
                "Prefer": "wait",
            },
            json={
                "input": {
                    "prompt": (
                        "Enhance this into a detailed, visual image prompt for an "
                        "NSFW image generator. Be explicit about appearance, style, "
                        "lighting, and composition, but keep it under 60 words: "
                        f"{user_prompt}"
                    )
                }
            },
            timeout=40,
        )
        r.raise_for_status()
        out = r.json().get("output", "")
        if isinstance(out, list):
            out = "".join(out)
        return jsonify({"enhanced_prompt": out.strip()})
    except Exception as e:
        print("Enhance error:", repr(e))
        return jsonify({"error": "Enhance failed"}), 500

# ---- IMAGE GENERATION (RUNPOD FLUX) ----
@app.route("/generate", methods=["POST"])
def generate():
    data = request.get_json()
    prompt = (data or {}).get("prompt", "").strip()
    negative_prompt = (data or {}).get("negative_prompt", "").strip()
    aspect_ratio = (data or {}).get("aspect_ratio", "1:1")
    seed = (data or {}).get("seed") or 0

    if not prompt:
        return jsonify({"error": "No prompt provided"}), 400

    payload = {
        "input": {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "aspect_ratio": aspect_ratio,
            "seed": seed,
        }
    }

    try:
        r = requests.post(
            f"https://api.runpod.ai/v2/{RUNPOD_ENDPOINT_ID}/run",
            json=payload,
            headers={"Authorization": f"Bearer {RUNPOD_API_KEY}"},
            timeout=40,
        )
        r.raise_for_status()
        job = r.json()
        job_id = job.get("id") or job.get("jobId")

        # simple polling loop
        while True:
            s = requests.post(
                f"https://api.runpod.ai/v2/{RUNPOD_ENDPOINT_ID}/status",
                json={"id": job_id},
                headers={"Authorization": f"Bearer {RUNPOD_API_KEY}"},
                timeout=40,
            )
            s.raise_for_status()
            status = s.json()
            if status.get("status") == "COMPLETED":
                output = status["output"]
                # assume base64 image string returned
                b64 = output.get("image") or output.get("image_base64")
                filename = f"static/{uuid.uuid4().hex}.png"
                os.makedirs("static", exist_ok=True)
                with open(filename, "wb") as f:
                    f.write(base64.b64decode(b64))
                return jsonify({"image_url": "/" + filename})
            elif status.get("status") in ("FAILED", "CANCELLED"):
                return jsonify({"error": "Generation failed"}), 500
    except Exception as e:
        print("Generate error:", repr(e))
        return jsonify({"error": "Generation failed"}), 500

# ---- A1111 PROXY (OPTIONAL) ----
@app.route("/a1111/proxy", methods=["POST"])
def a1111_proxy():
    if not A1111URL:
        return jsonify({"error": "A1111URL not configured"}), 500
    try:
        payload = request.get_json() or {}
        r = requests.post(
            A1111URL.rstrip("/") + "/sdapi/v1/txt2img",
            json=payload,
            timeout=40,
        )
        r.raise_for_status()
        return jsonify(r.json())
    except Exception as e:
        print("A1111 error:", repr(e))
        return jsonify({"error": "A1111 failed"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
