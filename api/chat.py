
from http.server import BaseHTTPRequestHandler
import json
import os
from openai import OpenAI

# Set up the client to point to NVIDIA's API
client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.environ.get("NVIDIA_API_KEY")
)

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data)
        user_message = data.get('message', '')

        try:
            with open("./knowledge.txt", "r", encoding="utf-8") as file:
                website_data = file.read()
        except:
            website_data = "No website data available."

        system_prompt = (
            "You are a helpful assistant for a personal website. "
            "Use the following website information to answer the user's question. "
            "If the answer is not in the information, say 'I am sorry, I don't have that information right now.'\n\n"
            f"WEBSITE INFORMATION:\n{website_data}"
        )

        try:
            response = client.chat.completions.create(
                model="meta/llama-3.1-8b-instruct",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                max_tokens=150
            )
            bot_response = response.choices[0].message.content
        except Exception as e:
            bot_response = f"DEBUG ERROR: {str(e)}"

        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps({"reply": bot_response}).encode('utf-8'))
        return
