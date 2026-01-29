from flask import Flask, request, jsonify, render_template_string
import requests
import os
import time

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")

openrouter_key = os.getenv("OPENROUTER_API_KEY", "").strip()
replicate_key = os.getenv("REPLICATE_API_KEY", "").strip()

# Uncensored-style model on OpenRouter (single, correct line)
enhance_model = "meta-llama/llama-3.1-8b-instruct"
# or
enhance_model = "nousresearch/hermes-3-llama-3.1-8b"



CSS = """
body { background-color: #0d0d0d; color: #ddd; font-family: Arial, sans-serif; margin: 0; padding: 20px; }
.container { max-width: 800px; margin: 0 auto; }
h1 { color: #f4444; font-size: 2.5em; margin-bottom: 10px; }
.tagline { color: #888; margin-bottom: 30px; }
textarea {
    background-color: #1a1a1a; color: #eee; border: 2px solid #444;
    border-radius: 8px; width: 100%; min-height: 120px; padding: 15px;
    font-size: 16px; box-sizing: border-box;
}
.button-row { display: flex; gap: 10px; margin: 15px 0; }
button {
    background: linear-gradient(145deg, #ab0000, #b22222); color: white;
    border: none; border-radius: 8px; padding: 15px 30px;
    font-weight: 600; font-size: 16px; cursor: pointer; flex: 1;
}
button:hover { background: linear-gradient(145deg, #a00000, #d32f2f); }
button:disabled { background: #333; color: #777; cursor: not-allowed; }
.generate-btn { width: 100%; font-size: 18px; padding: 18px; }
.result-box {
    background: #1a1a1a; border: 2px solid #444; border-radius: 8px;
    padding: 20px; margin: 20px 0;
}
.result-box img {
    max-width: 100%; border-radius: 8px;
    box-shadow: 0 10px 30px rgba(255,0,0,0.3);
}
.image-container { margin: 20px 0; text-align: center; }
.image-container img {
    max-width: 100%; border-radius: 8px;
    box-shadow: 0 10px 30px rgba(255,68,68,0.3);
}
.error { color: #ff4444; background: #2a1a1a; padding: 15px; border-radius: 8px; margin: 15px 0; }
.success { color: #44ff44; background: #1a2a1a; padding: 15px; border-radius: 8px; margin: 15px 0; }
"""

MAIN_HTML = f"""<html>
<head>
<title>Simple Image Generator</title>
<style>{CSS}</style>
</head>
<body>
<div class="container">
<h1>Simple Image</h1>
<p class="tagline">A human-friendly image generator</p>

<textarea id="prompt" placeholder="Describe your image..." rows="3"></textarea>
<div class="button-row">
<button id="enhanceBtn" onclick="enhance()">ENHANCE</button>
</div>
<button class="generate-btn" id="generateBtn" onclick="generate()">GENERATE IMAGE</button>

<div id="result"></div>
</div>

<script>
function enhance() {{
    const prompt = document.getElementById('prompt').value;
    if (!prompt) {{ alert('Please enter a description first'); return; }}
    
    const btn = document.getElementById('enhanceBtn');
    btn.disabled = true;
    btn.textContent = 'ENHANCING...';
    document.getElementById('result').innerHTML = '<div class="success">Enhancing your prompt...</div>';
    
    fetch('/enhance', {{
        method: 'POST',
        headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify({{prompt: prompt}})
    }})
    .then(r => r.json())
    .then(data => {{
        if (data.error) {{
            document.getElementById('result').innerHTML = '<div class="error">Error: ' + data.error + '</div>';
        }} else {{
            document.getElementById('prompt').value = data.enhanced;
            document.getElementById('result').innerHTML = '<div class="success">Prompt enhanced!</div>';
        }}
    }})
    .catch(e => {{
        document.getElementById('result').innerHTML = '<div class="error">Enhancement failed: ' + e + '</div>';
    }})
    .finally(() => {{
        btn.disabled = false;
        btn.textContent = 'ENHANCE';
    }});
}}

function generate() {{
    const prompt = document.getElementById('prompt').value;
    if (!prompt) {{ alert('Please enter a description first'); return; }}
    
    const btn = document.getElementById('generateBtn');
    btn.disabled = true;
    btn.textContent = 'GENERATING...';
    document.getElementById('result').innerHTML = '<div class="success">Generating image... this may take 30-60 seconds</div>';
    
    fetch('/generate', {{
        method: 'POST',
        headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify({{prompt: prompt}})
    }})
    .then(r => r.json())
    .then(data => {{
        if (data.error) {{
            document.getElementById('result').innerHTML = '<div class="error">Error: ' + data.error + '</div>';
        }} else if (data.image_url) {{
            document.getElementById('result').innerHTML = '<div class="image-container"><img src="' + data.image_url + '" alt="Generated"/></div>';
        }}
    }})
    .catch(e => {{
        document.getElementById('result').innerHTML = '<div class="error">Generation failed: ' + e + '</div>';
    }})
    .finally(() => {{
        btn.disabled = false;
        btn.textContent = 'GENERATE IMAGE';
    }});
}}
</script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(MAIN_HTML)

@app.route('/enhance', methods=['POST'])
def enhance():
    try:
        data = request.get_json()
        prompt = data.get('prompt', '')

        if not openrouter_key:
            return jsonify({'error': 'OPENROUTER_API_KEY not configured'}), 500

        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {openrouter_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": enhance_model,
                "messages": [{
                    "role": "user",
                    "content": (
                        "Enhance this image description to be more vivid and detailed "
                        "for an AI image generator. Keep it under 200 words. "
                        "Just return the enhanced description, nothing else:\n\n"
                        f"{prompt}"
                    )
                }],
                "max_tokens": 300
            },
            timeout=30
        )

        if response.status_code != 200:
            return jsonify({'error': f'OpenRouter API error: {response.status_code} - {response.text}'}), 500

        result = response.json()
        enhanced = result['choices'][0]['message']['content'].strip()
        return jsonify({'enhanced': enhanced})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/generate', methods=['POST'])
def generate():
    try:
        data = request.get_json()
        prompt = data.get('prompt', '')

        if not replicate_key:
            return jsonify({'error': 'REPLICATE_API_KEY not configured'}), 500

        response = requests.post(
            "https://api.replicate.com/v1/models/black-forest-labs/flux-schnell/predictions",
            headers={
                "Authorization": f"Token {replicate_key}",
                "Content-Type": "application/json"
            },
            json={
                "input": {
                    "prompt": prompt,
                    "num_outputs": 1,
                    "aspect_ratio": "1:1",
                    "output_format": "png"
                }
            },
            timeout=10
        )

        if response.status_code != 201:
            return jsonify({'error': f'Replicate API error: {response.status_code} - {response.text}'}), 500

        prediction = response.json()
        get_url = prediction.get('urls', {}).get('get')

        # Poll for completion
        for _ in range(60):
            time.sleep(2)
            status_response = requests.get(
                get_url,
                headers={"Authorization": f"Token {replicate_key}"},
                timeout=10
            )

            if status_response.status_code != 200:
                continue

            status_data = status_response.json()
            status = status_data.get('status')

            if status == 'succeeded':
                output = status_data.get('output', [])
                if output and len(output) > 0:
                    return jsonify({'image_url': output[0]})
                return jsonify({'error': 'No image output received'}), 500

            elif status == 'failed':
                error_msg = status_data.get('error', 'Unknown error')
                return jsonify({'error': f'Generation failed: {error_msg}'}), 500

        return jsonify({'error': 'Generation timed out'}), 500

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/test-key', methods=['GET'])
def test_key():
    if not openrouter_key:
        return jsonify({'status': 'No OPENROUTER_API_KEY loaded'}), 500

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {openrouter_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": enhance_model,
                "messages": [{"role": "user", "content": "test"}],
                "max_tokens": 5
            },
            timeout=15
        )
        return jsonify({
            "status_code": response.status_code,
            "response_preview": response.text[:400]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
