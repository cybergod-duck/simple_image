import flask
from flask import Flask, request, session, render_template_string
import requests
import os
import time

app = Flask(__name__)
app.secret_key = os.urandom(24)

replicate_api_key = os.getenv("REPLICATE_API_KEY", "").strip()

CSS = """
body {
    background-color: #0d0d0d;
    color: #ddd;
    font-family: Arial, sans-serif;
    margin: 0;
    padding: 0;
}

button {
    background: linear-gradient(145deg, #8b0000, #b22222);
    color: white;
    border: none;
    border-radius: 8px;
    padding: 12px 28px;
    font-weight: 600;
    box-shadow: 0 4px 12px rgba(139, 0, 0, 0.4);
    cursor: pointer;
    margin: 5px;
}

button:hover {
    background: linear-gradient(145deg, #a00000, #d32f2f);
}

textarea {
    background-color: #1a1a1a;
    color: #eee;
    border: 1px solid #444;
    border-radius: 6px;
    width: 100%;
    height: 140px;
    font-family: Arial, sans-serif;
    padding: 10px;
    font-size: 14px;
}

.sidebar {
    background-color: #111;
    padding: 20px;
    float: left;
    width: 250px;
}

.main {
    margin-left: 280px;
    padding: 20px;
}

.polaroid {
    position: relative;
    background: #f8f8f8;
    padding: 14px 14px 40px;
    border: 1px solid #ccc;
    border-bottom: 45px solid #eee;
    border-radius: 3px;
    box-shadow: 0 10px 25px rgba(0,0,0,0.7), inset 0 0 15px rgba(0,0,0,0.15);
    margin: 32px auto;
    max-width: 92%;
    animation: polaroid-develop 4s ease-out forwards;
    opacity: 0;
    transform: scale(0.92) rotate(1.8deg);
}

.polaroid:nth-child(even) {
    transform: scale(0.92) rotate(-1.8deg);
}

.polaroid img {
    width: 100%;
    border: 1px solid #222;
    box-shadow: inset 0 0 8px rgba(0,0,0,0.5);
}

.polaroid .caption {
    position: absolute;
    bottom: 12px;
    left: 0;
    right: 0;
    text-align: center;
    color: #333;
    font-family: Courier New, monospace;
    font-size: 0.95em;
    font-style: italic;
}

@keyframes polaroid-develop {
    0% {
        opacity: 0;
        filter: brightness(0.1) contrast(0.3) sepia(0.8) blur(10px);
        transform: scale(0.88) rotate(1.8deg);
    }
    30% {
        opacity: 0.25;
        filter: brightness(0.5) contrast(0.6) sepia(0.4) blur(5px);
        transform: scale(0.94);
    }
    65% {
        opacity: 0.75;
        filter: brightness(0.9) contrast(0.9) sepia(0.1) blur(1px);
    }
    100% {
        opacity: 1;
        filter: brightness(1) contrast(1) sepia(0) blur(0);
        transform: scale(1) rotate(1.8deg);
    }
}

.enhanced-box {
    background: #1a1a1a;
    border-left: 3px solid #b22222;
    padding: 12px;
    margin: 20px 0;
    border-radius: 6px;
    color: #888;
}

.spinner {
    border: 4px solid #333;
    border-top: 4px solid #b22222;
    border-radius: 50%;
    width: 24px;
    height: 24px;
    animation: spin 1s linear infinite;
    display: inline-block;
    margin-right: 10px;
}

@keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}

.error {
    color: #ff5959;
    font-weight: bold;
}

.success {
    color: #22c55e;
    font-weight: bold;
}
"""

MAIN_HTML = """
<html>
<head>
    <title>Simple-Image</title>
    <style>{CSS}</style>
</head>
<body>
    <aside class="sidebar">
        <h2>🍊 Simple-Image</h2>
        <p><strong>Unlimited</strong></p>
        
        <label>Image Size
            <select name="image_size">
                <option {selected_square}>Square (1024x1024)</option>
                <option {selected_portrait}>Portrait (768x1024)</option>
                <option {selected_landscape}>Landscape (1024x768)</option>
            </select>
        </label>
        
        <hr>
        <h4>Owner Login</h4>
        <form method="post" style="margin-top: 10px;">
            <input type="password" name="pw" placeholder="Password" style="width: 100%; padding: 8px; margin-bottom: 5px; background: #1a1a1a; border: 1px solid #444; color: #eee; border-radius: 4px;">
            <button type="submit" name="owner_login" style="width: 100%; margin: 0;">Unlock</button>
        </form>
        {error}
        {success}
        
        <hr>
        <p style="font-size: 0.85em; color: #666;">Powered by Replicate Flux</p>
    </aside>
    
    <main class="main">
        <h1>🍊 Simple-Image</h1>
        <p>Describe what you want. AI generates it in 1-2 minutes.</p>
        
        <form method="post">
            <textarea name="desc" placeholder="A beautiful sunset over mountains...">{desc}</textarea>
            
            <div style="display: flex; gap: 10px; margin-top: 15px; flex-wrap: wrap;">
                <button type="submit" name="enhance">ENHANCE</button>
                <button type="submit" name="nsfw">NSFW</button>
                <button type="submit" name="generate" style="flex: 1; min-width: 180px;">GENERATE</button>
            </div>
            
            {error_main}
            {status}
            {enhanced_prompt}
            {images_html}
            
            <hr>
            <p style="font-size: 0.9em; color: #666;">Simple-Image - Instant AI Generation | Atlanta | 2026</p>
        </form>
    </main>
</body>
</html>
"""

def enhance_prompt(desc: str) -> str:
    """Enhance prompt using Mistral 7B via Replicate"""
    if not replicate_api_key:
        return None
    
    prompt_text = (
        f"You are an elite prompt engineer. Make this image description more vivid, detailed, and specific: {desc}\n\n"
        f"Output ONLY the enhanced prompt:"
    )
    
    headers = {"Authorization": f"Bearer {replicate_api_key}"}
    payload = {
        "model": "mistralai/mistral-7b-instruct-v0.1",
        "input": {
            "prompt": prompt_text,
            "max_tokens": 500,
            "temperature": 0.7,
        }
    }
    
    try:
        r = requests.post("https://api.replicate.com/v1/predictions", headers=headers, json=payload, timeout=30)
        r.raise_for_status()
        pred_id = r.json()["id"]
        
        for _ in range(120):
            time.sleep(1)
            status_r = requests.get(f"https://api.replicate.com/v1/predictions/{pred_id}", headers=headers, timeout=10)
            status_r.raise_for_status()
            status_data = status_r.json()
            
            if status_data["status"] == "succeeded":
                output = status_data.get("output", [])
                if output:
                    return "".join(output).strip()
            elif status_data["status"] == "failed":
                return None
        
        return None
    except:
        return None

def generate_image(prompt: str, image_size: str):
    """Generate image using Flux Pro via Replicate"""
    if not replicate_api_key:
        return None, "API key missing"
    
    size_map = {
        "Square (1024x1024)": "1024x1024",
        "Portrait (768x1024)": "768x1024",
        "Landscape (1024x768)": "1024x768",
    }
    
    headers = {"Authorization": f"Bearer {replicate_api_key}"}
    payload = {
        "model": "black-forest-labs/flux-pro",
        "input": {
            "prompt": prompt,
            "image_size": size_map.get(image_size, "1024x1024"),
            "num_outputs": 1,
        }
    }
    
    try:
        r = requests.post("https://api.replicate.com/v1/predictions", headers=headers, json=payload, timeout=30)
        r.raise_for_status()
        pred_id = r.json()["id"]
        
        for _ in range(60):
            time.sleep(5)
            status_r = requests.get(f"https://api.replicate.com/v1/predictions/{pred_id}", headers=headers, timeout=10)
            status_r.raise_for_status()
            status_data = status_r.json()
            
            if status_data["status"] == "succeeded":
                outputs = status_data.get("output", [])
                return outputs[0] if outputs else None, None
            elif status_data["status"] == "failed":
                return None, "Generation failed"
        
        return None, "Timeout"
    except Exception as e:
        return None, str(e)

@app.route("/", methods=["GET", "POST"])
def index():
    session.setdefault("logged_in", True)
    
    error = success = error_main = status = enhanced_prompt = ""
    
    if request.method == "POST" and "owner_login" in request.form:
        pw = request.form.get("pw", "").lower()
        if pw == "owner-unlocked":
            success = '<p class="success">✓ Owner unlocked</p>'
        else:
            error = '<p class="error">Wrong password</p>'
    
    images_html = ""
    desc = session.get("desc", "")
    image_size = session.get("image_size", "Square (1024x1024)")
    
    if request.method == "POST":
        desc = request.form.get("desc", desc).strip()
        session["desc"] = desc
        image_size = request.form.get("image_size", image_size)
        session["image_size"] = image_size
        
        if "enhance" in request.form:
            if not desc:
                error_main = '<p class="error">Enter description first</p>'
            else:
                status = '<div><span class="spinner"></span>Enhancing...</div>'
                enhanced = enhance_prompt(desc)
                status = ""
                if enhanced:
                    desc = enhanced
                    session["desc"] = desc
                    enhanced_prompt = f'<div class="enhanced-box"><strong>✓ Enhanced:</strong><br>{enhanced}</div>'
                else:
                    error_main = '<p class="error">Enhancement failed</p>'
        
        elif "nsfw" in request.form:
            desc = "NSFW, explicit: " + desc
            session["desc"] = desc
        
        if "generate" in request.form:
            if not desc:
                error_main = '<p class="error">Describe what you want</p>'
            elif not replicate_api_key:
                error_main = '<p class="error">API key not set</p>'
            else:
                status = '<div><span class="spinner"></span>Generating... 1-2 minutes</div>'
                img_url, img_err = generate_image(desc, image_size)
                status = ""
                if img_url:
                    images_html = f'<div class="polaroid"><img src="{img_url}"><div class="caption">Generated</div></div>'
                else:
                    error_main = f'<p class="error">Error: {img_err}</p>'
    
    selected_square = "selected" if image_size == "Square (1024x1024)" else ""
    selected_portrait = "selected" if image_size == "Portrait (768x1024)" else ""
    selected_landscape = "selected" if image_size == "Landscape (1024x768)" else ""
    
    return render_template_string(
        MAIN_HTML.format(
            CSS=CSS,
            selected_square=selected_square,
            selected_portrait=selected_portrait,
            selected_landscape=selected_landscape,
            desc=desc,
            error=error,
            success=success,
            error_main=error_main,
            status=status,
            enhanced_prompt=enhanced_prompt,
            images_html=images_html,
        )
    )

if __name__ == "__main__":
    app.run(debug=True)
