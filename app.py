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

.loading {
    text-align: center;
    padding: 20px;
    color: #888;
}

.spinner {
    border: 4px solid #333;
    border-top: 4px solid #b22222;
    border-radius: 50%;
    width: 30px;
    height: 30px;
    animation: spin 1s linear infinite;
    margin: 20px auto;
}

@keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
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
        
        <select name="image_size">
            <option {selected_square}>Square (1024x1024)</option>
            <option {selected_portrait}>Portrait (768x1024)</option>
            <option {selected_landscape}>Landscape (1024x768)</option>
        </select>
        
        <hr>
        <h4>Owner Login</h4>
        <form method="post" style="max-width: 100%;">
            <input type="password" name="pw" placeholder="Owner password" style="width: 100%; padding: 8px; margin-bottom: 5px;">
            <button type="submit" name="owner_login" style="width: 100%; margin: 0;">Unlock</button>
        </form>
        {error}
        {success}
        
        <hr>
        <p style="font-size: 0.9em; color: #999;">Powered by Replicate Flux</p>
    </aside>
    
    <main class="main">
        <h1>🍊 Simple-Image</h1>
        <p>Describe what you want. AI generates it in 1-2 minutes.</p>
        
        <form method="post" enctype="multipart/form-data">
            <textarea name="desc" placeholder="A beautiful sunset over mountains...">{desc}</textarea>
            
            <div style="display: flex; justify-content: space-around; margin-top: 10px;">
                <button type="submit" name="generate" style="margin-top: 0; width: auto;">GENERATE</button>
            </div>
            
            {error_main}
            {status}
            {images_html}
            
            <hr>
            <p>Simple-Image - Instant AI Generation | Atlanta | 2026</p>
        </form>
    </main>
</body>
</html>
"""

def generate_image(prompt: str, image_size: str):
    if not replicate_api_key:
        return None, "Error: REPLICATE_API_KEY missing"
    
    size_map = {
        "Square (1024x1024)": "square",
        "Portrait (768x1024)": "portrait",
        "Landscape (1024x768)": "landscape",
    }
    size = size_map.get(image_size, "square")
    
    headers = {"Authorization": f"Bearer {replicate_api_key}", "Content-Type": "application/json"}
    payload = {
        "model": "black-forest-labs/flux-pro",
        "input": {
            "prompt": prompt,
            "image_size": size,
            "num_outputs": 1,
            "guidance_scale": 7.5,
        }
    }
    
    try:
        r = requests.post("https://api.replicate.com/v1/predictions", headers=headers, json=payload, timeout=30)
        r.raise_for_status()
        data = r.json()
        prediction_id = data["id"]
        
        for attempt in range(60):
            time.sleep(5)
            status_r = requests.get(f"https://api.replicate.com/v1/predictions/{prediction_id}", headers=headers, timeout=10)
            status_r.raise_for_status()
            status_data = status_r.json()
            
            if status_data["status"] == "succeeded":
                outputs = status_data.get("output", [])
                if outputs:
                    return outputs[0], None
                else:
                    return None, "Error: No output"
            elif status_data["status"] == "failed":
                return None, f"Error: {status_data.get('error', 'Failed')}"
        
        return None, "Error: Timeout"
    except Exception as e:
        return None, f"Error: {str(e)}"

@app.route("/", methods=["GET", "POST"])
def index():
    session.setdefault("logged_in", True)
    session.setdefault("credits", float('inf'))
    
    error = success = error_main = status = ""
    
    if request.method == "POST" and "owner_login" in request.form:
        pw = request.form.get("pw", "").lower()
        if pw == "owner-unlocked":
            success = '<p style="color:green;">✓ Owner unlocked</p>'
        else:
            error = '<p style="color:red;">Wrong password</p>'
    
    images_html = ""
    desc = session.get("desc", "")
    image_size = session.get("image_size", "Square (1024x1024)")
    
    if request.method == "POST":
        desc = request.form.get("desc", desc).strip()
        session["desc"] = desc
        image_size = request.form.get("image_size", image_size)
        session["image_size"] = image_size
        
        if "generate" in request.form:
            if not desc:
                error_main = '<p style="color:red;">Describe what you want</p>'
            elif not replicate_api_key:
                error_main = '<p style="color:red;">API key missing</p>'
            else:
                status = '<div class="loading"><div class="spinner"></div>Generating image... 1-2 minutes</div>'
                img_url, img_error = generate_image(desc, image_size)
                if img_error:
                    error_main = f'<p style="color:red;">{img_error}</p>'
                elif img_url:
                    images_html = f'<div class="polaroid"><img src="{img_url}" style="width:100%;border:1px solid #222;"><div class="caption">Generated</div></div>'
                    status = '<p style="color:green;">✓ Done!</p>'
    
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
            images_html=images_html,
        )
    )

if __name__ == "__main__":
    app.run(debug=True)
