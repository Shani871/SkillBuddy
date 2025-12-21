import os
import requests
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.conf import settings

@login_required
def chatbot_view(request):
    # Retrieve chat history from session or initialize it
    chat_history = request.session.get('chat_history', [])
    
    # We display results in a list to match the template's previous structure
    # but we store the full context for Gemini
    output_text = []

    if request.method == "POST":
        user_input = request.POST.get("user_input")
        
        # Security: Get API key from environment
        api_key = os.getenv("GEMINI_API_KEY")
        
        if not api_key:
            output_text = ["Error: GEMINI_API_KEY not found in environment. Please check your .env file."]
        else:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
            headers = {"Content-Type": "application/json"}

            # Build content with history for context
            contents = []
            for msg in chat_history[-10:]: # Keep last 10 messages for context
                contents.append({
                    "role": "user" if msg['role'] == 'user' else 'model',
                    "parts": [{"text": msg['text']}]
                })
            
            # Add current message
            contents.append({
                "role": "user",
                "parts": [{"text": user_input}]
            })

            payload = {"contents": contents}

            try:
                response = requests.post(url, json=payload, headers=headers, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    raw_text = data['candidates'][0]['content']['parts'][0]['text']
                    
                    # Update session history
                    chat_history.append({"role": "user", "text": user_input})
                    chat_history.append({"role": "model", "text": raw_text})
                    request.session['chat_history'] = chat_history
                    request.session.modified = True
                    
                    output_text = raw_text.split("\n")
                else:
                    output_text = [f"API Error ({response.status_code}): {response.text[:100]}"]
            except requests.exceptions.RequestException as e:
                output_text = [f"Connection Error: {str(e)}"]

    return render(request, "chatbot.html", {
        "response": output_text,
        "chat_history": chat_history
    })

def index(request):
    return render(request, "index.html")