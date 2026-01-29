import flask
from flask import Flask, request, session, render_template_string
import requests
import base64
import os
import time
import random

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Load environment variables
replicate_api_key = os.getenv("REPLICATE_API_KEY", "").strip()
runpod_api_key = os.getenv("RUNPOD_API_KEY", "").strip()
runpod_endpoint_id = os.getenv("RUNPOD_ENDPOINT_ID", "").strip()
a1111_url = os.getenv("A1111_URL", "").strip()

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

button:disabled {
    background: #333;
    color: #777;
    cursor: not-allowed;
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

.config-warning {
    background: #3c2f2f;
    border-left: 5px solid #b22222;
    padding: 16px;
    margin: 24px 0;
    border-radius: 6px;
    font-size: 1.05em;
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

.blurred {
    position: relative;
}

.blurred img {
    filter: blur(10px);
}

.blurred .overlay {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    background: rgba(0,0,0,0.7);
    color: white;
    padding: 20px;
    border-radius: 10px;
    text-align: center;
}
"""

LOGIN_HTML = """
<html>
<head>
    <title>Simple-Image</title>
    <style>{CSS}</style>
</head>
<body>
    <h1>🍊 Simple-Image</h1>
    <p>Create impressive images for free, or sign up for full access.</p>
    
    <form method="post">
        <label>Are you 18 or over?
            <input type="radio" name="age_confirm" value="yes"> Yes
            <input type="radio" name="age_confirm" value="no"> No
        </label><br>
        <button type="submit" name="signup">Sign Up</button>
    </form>
    
    <form method="post">
        <input type="password" name="pw" placeholder="Owner phrase">
        <button type="submit" name="login">Owner Login</button>
    </form>
    
    {error}
    {success}
</body>
</html>
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
        <p><strong>Credits:</strong> {credits}</p>
        
        <label>
            <input type="checkbox" name="use_controlnet" {checked_controlnet}>
            Enable ControlNet
        </label>
        
        <label>Denoising Strength
            <input type="range" name="denoising" min="0" max="1" step="0.05" value="{denoising}">
        </label>
        
        <select name="image_size">
            <option {selected_banner_wide}>Banner Wide (1920x300)</option>
            <option {selected_banner_narrow}>Banner Narrow (728x90)</option>
            <option {selected_square}>Square (1024x1024)</option>
            <option {selected_portrait}>Portrait (768x1024)</option>
        </select>
        
        <hr>
        <button type="submit" name="buy_credits">Buy More Credits</button>
        {buy_info}
    </aside>
    
    <main class="main">
        <h1>🍊 Simple-Image</h1>
        <p>Unfiltered. Hyper-realistic. No limits. Describe exactly what you want.</p>
        
        <form method="post" enctype="multipart/form-data">
            <textarea name="desc" placeholder="Describe the scene...">{desc}</textarea>
            
            <div style="display: flex; justify-content: space-around; margin-top: 10px;">
                <button type="submit" name="enhance">ENHANCE</button>
                <button type="submit" name="nsfw" {disabled_nsfw}>NSFW</button>
                <button type="submit" name="violence" {disabled_violence}>VIOLENCE</button>
                <input type="file" name="refs" multiple accept=".png,.jpg,.jpeg" style="display: none;" id="upload">
                <label for="upload" style="background: linear-gradient(145deg, #8b0000, #b22222); color: white; border: none; border-radius: 8px; padding: 12px 28px; font-weight: 600; box-shadow: 0 4px 12px rgba(139, 0, 0, 0.4); cursor: pointer;">UPLOAD</label>
            </div>
            
            <button type="submit" name="generate" style="margin-top: 20px; width: 100%;">GENERATE</button>
            
            {error}
            {generated_prompt}
            {images_html}
            
            <hr>
            <p>Simple-Image - Absolute freedom | Atlanta | 2026</p>
        </form>
    </main>
    {config_warning}
</body>
</html>
"""

NSFW_KEYWORDS = ["sexy", "nude", "naked", "porn", "erotic", "adult", "explicit"]

def is_nsfw(prompt: str) -> bool:
    return any(word in prompt.lower() for word in NSFW_KEYWORDS)

def generate_prompt(desc: str, mode: str = None) -> str:
    """Generate or enhance prompt using Replicate API (Mistral 7B)"""
    
    if mode == "enhance":
        system_prompt = (
            "You are an elite prompt engineer for image generation. "
            "Enhance the user description for better results, make it more detailed and vivid. "
            "Output ONLY the enhanced prompt."
        )
    else:
        scene_type = "hyper-explicit NSFW" if mode == "nsfw" else "graphic violence" if mode == "violence" else ""
        system_prompt = (
            f"You are an elite prompt engineer. Convert the user description into a {scene_type} scene. "
            f"Photorealistic, cinematic. Output ONLY the final prompt."
        )
    
    headers = {
        "Authorization": f"Bearer {replicate_api_key}",
    }
    
    payload = {
        "model": "mistral-7b",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": desc}
        ]
    }
    
    try:
        r = requests.post(
            "https://api.replicate.com/v1/messages",
            headers=headers,
            json=payload,
            timeout=60
        )
        r.raise_for_status()
        return r.json()["content"][0]["text"].strip()
    except requests.RequestException as e:
        app.logger.error(f"Replicate API error: {str(e)}")
        return f"Error: Failed to connect to Replicate API. {str(e)}"

def generate_image(prompt: str, refs, use_controlnet: bool, denoising: float, image_size: str, blur: bool = False):
    """Generate image using RunPod A1111 endpoint with polling"""
    
    if not runpod_api_key or not runpod_endpoint_id:
        return "Error: RunPod credentials missing. Set RUNPOD_API_KEY and RUNPOD_ENDPOINT_ID."
    
    if not refs:
        return "Warning: No reference images provided."
    
    ref_bytes = refs[0].read()
    init_img = base64.b64encode(ref_bytes).decode()
    
    size_map = {
        "Banner Wide (1920x300)": (1920, 300),
        "Banner Narrow (728x90)": (728, 90),
        "Square (1024x1024)": (1024, 1024),
        "Portrait (768x1024)": (768, 1024),
    }
    w, h = size_map.get(image_size, (768, 1024))
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {runpod_api_key}"
    }
    
    payload = {
        "input": {
            "prompt": prompt,
            "negative_prompt": "blurry, deformed, ugly",
            "steps": 35,
            "cfg_scale": 7,
            "sampler_name": "DPM++ 2M Karras",
            "width": w,
            "height": h,
            "denoising_strength": denoising,
            "init_images": [init_img],
        }
    }
    
    try:
        # Submit job to RunPod
        start_resp = requests.post(
            f"https://api.runpod.io/v2/{runpod_endpoint_id}/run",
            headers=headers,
            json=payload,
            timeout=30
        )
        start_resp.raise_for_status()
        job_id = start_resp.json()["id"]
        app.logger.info(f"RunPod job started: {job_id}")
        
        # Poll for completion (max 10 minutes)
        for attempt in range(240):  # 240 * 2.5s = 600s = 10 minutes
            time.sleep(2.5)
            
            status_resp = requests.get(
                f"https://api.runpod.io/v2/{runpod_endpoint_id}/status/{job_id}",
                headers=headers,
                timeout=10
            )
            status_resp.raise_for_status()
            status_data = status_resp.json()
            
            if status_data.get("status") == "COMPLETED":
                images = status_data.get("output", {}).get("images", [])
                if images:
                    images_html = ""
                    for i, b64 in enumerate(images):
                        img_src = f"data:image/png;base64,{b64}"
                        if blur:
                            images_html += f"""<div class="polaroid blurred"><img src="{img_src}"><div class="overlay">BUY CREDITS</div><div class="caption">Creation {i+1}</div></div>"""
                        else:
                            images_html += f"""<div class="polaroid"><img src="{img_src}"><div class="caption">Creation {i+1}</div></div>"""
                    return images_html
                else:
                    return "Error: RunPod returned no images."
            
            elif status_data.get("status") == "FAILED":
                return f"Error: Job failed - {status_data.get('error', 'Unknown error')}"
        
        return "Error: Generation timeout (10 minutes exceeded)"
    
    except requests.RequestException as e:
        return f"Error: RunPod API failed - {str(e)}"

@app.route("/", methods=["GET", "POST"])
def index():
    session.setdefault("logged_in", False)
    session.setdefault("credits", 10)
    session.setdefault("content_mode", None)
    
    config_warning = ""
    missing_keys = []
    
    if not replicate_api_key:
        missing_keys.append("REPLICATE_API_KEY")
    if not runpod_api_key:
        missing_keys.append("RUNPOD_API_KEY")
    if not runpod_endpoint_id:
        missing_keys.append("RUNPOD_ENDPOINT_ID")
    
    if missing_keys:
        config_warning = f"""
        <div class="config-warning">
            <strong>⚠️ Missing environment variables:</strong><br>
            {', '.join(missing_keys)}<br><br>
            Add these in Render → Environment Variables and redeploy.
        </div>
        """
    
    error = success = ""
    
    if request.method == "POST" and not session["logged_in"]:
        if "signup" in request.form:
            age = request.form.get("age_confirm", "").lower()
            if age == "yes":
                session["logged_in"] = True
                return flask.redirect("/")
            else:
                error = '<p style="color:red;">Must be 18+</p>'
        
        elif "login" in request.form:
            pw = request.form.get("pw", "").lower()
            if pw == "owner-unlocked":
                session["logged_in"] = True
                session["credits"] = float('inf')
                success = '<p style="color:green;">✓ Owner unlocked</p>'
                return flask.redirect("/")
    
    if not session["logged_in"]:
        return render_template_string(LOGIN_HTML.format(CSS=CSS, error=error, success=success))
    
    generated_prompt = images_html = buy_info = ""
    desc = session.get("desc", "")
    use_controlnet = session.get("use_controlnet", False)
    denoising = session.get("denoising", 0.35)
    image_size = session.get("image_size", "Portrait (768x1024)")
    content_mode = session.get("content_mode")
    
    if request.method == "POST":
        desc = request.form.get("desc", desc)
        session["desc"] = desc
        use_controlnet = "use_controlnet" in request.form
        session["use_controlnet"] = use_controlnet
        denoising = float(request.form.get("denoising", denoising))
        session["denoising"] = denoising
        image_size = request.form.get("image_size", image_size)
        session["image_size"] = image_size
        
        if "enhance" in request.form:
            time.sleep(random.uniform(1.5, 2.1))
            enhanced = generate_prompt(desc, mode="enhance")
            if "Error" not in enhanced:
                desc = enhanced
                session["desc"] = desc
                generated_prompt = f"<h2>Enhanced Prompt</h2><pre>{enhanced}</pre>"
            else:
                error = f'<p style="color:red;">{enhanced}</p>'
        
        elif "nsfw" in request.form and session["logged_in"]:
            session["content_mode"] = "nsfw"
        elif "violence" in request.form and session["logged_in"]:
            session["content_mode"] = "violence"
        
        elif "generate" in request.form:
            refs = request.files.getlist("refs")
            
            if not desc.strip():
                error = '<p style="color:red;">Need a description</p>'
            elif not replicate_api_key or not runpod_api_key or not runpod_endpoint_id:
                error = '<p style="color:red;">API keys missing</p>'
            else:
                session["credits"] -= 1
                
                time.sleep(random.uniform(1.5, 2.1))
                prompt = generate_prompt(desc, mode=content_mode if session["logged_in"] else None)
                
                if "Error" not in prompt:
                    generated_prompt = f"<h2>Generated Prompt</h2><pre>{prompt}</pre>"
                    time.sleep(random.uniform(2.4, 3.3))
                    images_html = generate_image(prompt, refs, use_controlnet, denoising, image_size)
                else:
                    error = f'<p style="color:red;">{prompt}</p>'
    
    credits = "∞" if session["credits"] == float('inf') else int(session["credits"])
    checked_controlnet = "checked" if use_controlnet else ""
    selected_banner_wide = "selected" if image_size == "Banner Wide (1920x300)" else ""
    selected_banner_narrow = "selected" if image_size == "Banner Narrow (728x90)" else ""
    selected_square = "selected" if image_size == "Square (1024x1024)" else ""
    selected_portrait = "selected" if image_size == "Portrait (768x1024)" else ""
    disabled_nsfw = "" if session["logged_in"] else "disabled"
    disabled_violence = "" if session["logged_in"] else "disabled"
    
    return render_template_string(
        MAIN_HTML.format(
            CSS=CSS,
            credits=credits,
            checked_controlnet=checked_controlnet,
            denoising=denoising,
            selected_banner_wide=selected_banner_wide,
            selected_banner_narrow=selected_banner_narrow,
            selected_square=selected_square,
            selected_portrait=selected_portrait,
            desc=desc,
            disabled_nsfw=disabled_nsfw,
            disabled_violence=disabled_violence,
            error=error,
            generated_prompt=generated_prompt,
            images_html=images_html,
            buy_info=buy_info,
            config_warning=config_warning
        )
    )

if __name__ == "__main__":
    app.run(debug=True)
