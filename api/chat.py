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
            page_content = data.get('pageContent', 'No website content provided.')[:4000] 
            chat_history = data.get('history', [])
            image_base64 = data.get('image', None)

            from openai import OpenAI
            api_key = os.environ.get("NVIDIA_API_KEY")
            if not api_key:
                raise Exception("NVIDIA_API_KEY is missing!")
                
            client = OpenAI(
                base_url="https://integrate.api.nvidia.com/v1",
                api_key=api_key
            )

            # READ THE GLOBAL KNOWLEDGE FILE (Info from ALL pages)
            try:
                with open("./knowledge.txt", "r", encoding="utf-8") as file:
                    global_knowledge = file.read()
            except:
                global_knowledge = "No global knowledge available."

            system_prompt = (
                "You are Bilal's personal AI assistant. "
                "Your job is to answer questions STRICTLY based on the provided WEBSITE KNOWLEDGE and the CURRENT PAGE TEXT. "
                "STRICT RULE: NEVER mention the Privacy Policy, chat windows, or website layouts. "
                "Focus ONLY on Bilal's projects, skills, services, pricing plans, and contact info. "
                "Whenever you refer to the website owner, use the name Bilal. "
                "Do NOT start your response with phrases like 'According to the website'. "
                "If the answer is genuinely not in the text, say 'I am sorry, I don\\'t have that information right now.'\n\n"
                f"WEBSITE KNOWLEDGE (All Pages):\n{global_knowledge}\n\n"
                f"CURRENT PAGE TEXT:\n{page_content}\n\n"
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
                temperature=0.3
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
