import requests
import json
import os

API_KEY = "fw_HSBGGfMhBoifF4P8QydBcr"
URL = "https://api.fireworks.ai/inference/v1/chat/completions"
MODEL = "accounts/fireworks/models/qwen2p5-72b-instruct"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

payload = {
    "model": MODEL,
    "messages": [{"role": "user", "content": "Hello!"}],
    "max_tokens": 10
}

try:
    print(f"Sending request to {URL} with model {MODEL}...")
    response = requests.post(URL, headers=headers, json=payload)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")
