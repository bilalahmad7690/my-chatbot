from http.server import BaseHTTPRequestHandler
import json
import os

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_POST(self):
        try:
            # 1. Get the user message AND the website content
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data)
            
            user_message = data.get('message', 'Hello')
            # This grabs the website text sent from the browser
            website_data = data.get('pageContent', 'No website content provided.')[:3000] # Limit to 3000 characters to save space

            # 2. Initialize OpenAI client
            from openai import OpenAI
            api_key = os.environ.get("NVIDIA_API_KEY")
            if not api_key:
                raise Exception("NVIDIA_API_KEY is missing in Vercel Environment Variables!")
                
            client = OpenAI(
                base_url="https://integrate.api.nvidia.com/v1",
                api_key=api_key
            )

            system_prompt = (
                "You are a helpful assistant for a personal website. "
                "Use the following website page content to answer the user's question. "
                "If the answer is not in the information, say 'I am sorry, I don't have that information right now.'\n\n"
                f"WEBSITE PAGE CONTENT:\n{website_data}"
            )

            # 3. Ask NVIDIA AI for response
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
            bot_response = f"SERVER ERROR: {str(e)}"

        # 4. Send response back to WordPress
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        response_data = json.dumps({"reply": bot_response})
        self.wfile.write(response_data.encode('utf-8'))
        return
