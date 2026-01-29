from flask import Flask, request, session, render_template_string
import requests
import os
import time

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")

# Load environment variables
openrouter_key = os.getenv("OPENROUTER_API_KEY", "").strip()
replicate_key = os.getenv("REPLICATE_API_KEY", "").strip()

# Use free Mistral model
enhance_model = "mistralai/mistral-7b-instruct:free"

CSS = """
body { background-color: #0d0d0d; color: #ddd; font-family: Arial, sans-serif; margin: 0; padding: 20px; }
.container { max-width: 800px; margin: 0 auto; }
h1 { color: #ff4444; font-size: 2.5em; margin-bottom: 10px; }
.tagline { color: #888; margin-bottom: 30px; }
textarea {
    background-color: #1a1a1a;
    color: #eee;
    border: 2px solid #444;
    border-radius: 8px;
    width: 100%;
    min-height: 120px;
    padding: 15px;
    font-size: 16px;
    font-family: Arial, sans-serif;
    box-sizing: border-box;
}
.button-row {
    display: flex;
    gap: 10px;
    margin: 15px 0;
}
button {
    background: linear-gradient(145deg, #8b0000, #b22222);
    color: white;
    border: none;
    border-radius: 8px;
    padding: 15px 30px;
    font-weight: 600;
    font-size: 16px;
    cursor: pointer;
    transition: all 0.3s;
    flex: 1;
}
button:hover { 
    background: linear-gradient(145deg, #a00000, #d32f2f); 
    transform: translateY(-2px);
}
button:disabled {
    background: #333;
    color: #777;
    cursor: not-allowed;
    transform: none;
}
.generate-btn {
    width: 100%;
    font-size: 18px;
    padding: 18px;
}
.result-box {
    background: #1a1a1a;
    border: 2px solid #444;
    border-radius: 8px;
    padding: 20px;
    margin: 20px 0;
}
.result-box h3 {
    color: #ff4444;
    margin-top: 0;
}
.result-box pre {
    color: #eee;
    white-space: pre-wrap;
    word-wrap: break-word;
}
.image-container {
    margin: 20px 0;
    text-align: center;
}
.image-container img {
    max-width: 100%;
    border-radius: 8px;
