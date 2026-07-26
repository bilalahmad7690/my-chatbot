from http.server import BaseHTTPRequestHandler
import json
import os
import re

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_POST(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data)
            
            user_message = data.get('message', 'Hello')
            # JS now sends the ENTIRE website text here
            page_content = data.get('pageContent', 'No website content provided.')[:15000] 
            chat_history = data.get('history', [])
            image_base64 = data.get('image', None)
            site_name = data.get('siteName', 'this website')

            from openai import OpenAI
            api_key = os.environ.get("NVIDIA_API_KEY")
            if not api_key:
                raise Exception("NVIDIA_API_KEY is missing!")
                
            client = OpenAI(
                base_url="https://integrate.api.nvidia.com/v1",
                api_key=api_key
            )

            system_prompt = (
                f"You are the helpful AI assistant for {site_name}. "
                "Your job is to answer questions based on the provided WEBSITE TEXT. "
                "STRICT RULE: NEVER mention the Privacy Policy, chat windows, or website layouts. "
                "Focus ONLY on the website's projects, skills, services, pricing plans, and contact info. "
                f"Whenever you refer to the website owner, use the name {site_name}. "
                "If the user asks for a service or pricing, scan the text for related keywords. "
                "If a matching or related service exists, confidently confirm that you offer it and provide details from the text. "
                "Do NOT start your response with phrases like 'According to the website'. "
                "If the answer is absolutely not in the text after careful analysis, say 'I am sorry, I don\\'t have that information right now.'\n\n"
                f"WEBSITE TEXT:\n{page_content}\n\n"
                "IMPORTANT INSTRUCTION: At the very end of your response, you MUST provide 3 short suggested questions. "
                "Format them exactly like this on a new line: SUGGESTIONS: Question 1?, Question 2?, Question 3?"
            )

            messages = [{"role": "system", "content": system_prompt}]
            for msg in chat_history:
                if msg.get('user'): messages.append({"role": "user", "content": msg.get('user')})
                if msg.get('bot'): messages.append({"role": "assistant", "content": msg.get('bot')})

            if image_base64:
                model_name = "meta/llama-3.2-11b-vision-instruct"
                user_content = [
                    {"type": "text", "text": user_message if user_message else "What is in this image?"},
                    {"type": "image_url", "image_url": image_base64}
                ]
                messages.append({"role": "user", "content": user_content})
            else:
                model_name = "meta/llama-3.1-8b-instruct"
                messages.append({"role": "user", "content": user_message})

            response = client.chat.completions.create(
                model=model_name,
                messages=messages,
                max_tokens=400,
                temperature=0.4
            )
            full_response = response.choices[0].message.content

            match = re.search(r'SUGGESTIONS:\s*(.*)', full_response, re.IGNORECASE | re.DOTALL)
            if match:
                bot_response = full_response[:match.start()].strip()
                sugg_text = match.group(1)
                suggestions = [s.strip().replace('*', '') for s in re.split(r'[,\n]', sugg_text) if s.strip()][:3]
            else:
                bot_response = full_response
                suggestions = []

        except Exception as e:
            bot_response = f"SERVER ERROR: {str(e)}"
            suggestions = []

        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        response_data = json.dumps({"reply": bot_response, "suggestions": suggestions})
        self.wfile.write(response_data.encode('utf-8'))
        return
