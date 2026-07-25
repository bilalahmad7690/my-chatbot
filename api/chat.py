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
            # 1. Get data from website
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data)
            
            user_message = data.get('message', 'Hello')
            page_content = data.get('pageContent', 'No website content provided.')[:1500]
            chat_history = data.get('history', [])
            image_base64 = data.get('image', None) # NEW: Get image if uploaded

            # 2. Initialize NVIDIA AI
            from openai import OpenAI
            api_key = os.environ.get("NVIDIA_API_KEY")
            if not api_key:
                raise Exception("NVIDIA_API_KEY is missing!")
                
            client = OpenAI(
                base_url="https://integrate.api.nvidia.com/v1",
                api_key=api_key
            )

            system_prompt = (
                "You are an expert AI assistant for this website. "
                "Carefully analyze the following website page text to answer the user's question. "
                "Scan the entire text for names, projects, services, contact info, and pricing. "
                "If the answer is in the text, provide a clear, direct response. "
                "Do NOT start your response with phrases like 'According to the website content', 'Based on the text', or 'The website says'. Just give the answer directly. "
                "If the answer is genuinely not in the text, say 'I am sorry, I don't have that information right now.'\n\n"
                f"WEBSITE PAGE TEXT:\n{page_content}\n\n"
                "IMPORTANT INSTRUCTION: At the very end of your response, you MUST provide 3 short suggested questions the user might ask next. "
                "Format them exactly like this on a new line: SUGGESTIONS: Question 1?, Question 2?, Question 3?"
            )

            messages = [{"role": "system", "content": system_prompt}]
            for msg in chat_history:
                if msg.get('user'): messages.append({"role": "user", "content": msg.get('user')})
                if msg.get('bot'): messages.append({"role": "assistant", "content": msg.get('bot')})

            # 3. Decide which AI model to use (Vision vs Text)
            if image_base64:
                # Use Llama 3.2 Vision Model for images
                model_name = "meta/llama-3.2-11b-vision-instruct"
                user_content = [
                    {"type": "text", "text": user_message if user_message else "What is in this image?"},
                    {"type": "image_url", "image_url": image_base64}
                ]
                messages.append({"role": "user", "content": user_content})
            else:
                # Use standard Text Model
                model_name = "meta/llama-3.1-8b-instruct"
                messages.append({"role": "user", "content": user_message})

            # 4. Ask NVIDIA AI for response
            response = client.chat.completions.create(
                model=model_name,
                messages=messages,
                max_tokens=400,
                temperature=0.6
            )
            full_response = response.choices[0].message.content

            # 5. Separate the text reply from the suggestions
            if "SUGGESTIONS:" in full_response:
                parts = full_response.split("SUGGESTIONS:")
                bot_response = parts[0].strip()
                suggestions = [s.strip() for s in parts[1].split(",")][:3]
            else:
                bot_response = full_response
                suggestions = []

        except Exception as e:
            bot_response = f"SERVER ERROR: {str(e)}"
            suggestions = []

        # 6. Send response back to WordPress
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        response_data = json.dumps({"reply": bot_response, "suggestions": suggestions})
        self.wfile.write(response_data.encode('utf-8'))
        return
