import os
import requests
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.conf import settings

@login_required
def chatbot_view(request):
    if request.GET.get('clear') == '1':
        request.session['chat_history'] = []
        request.session.modified = True
        from django.shortcuts import redirect
        return redirect('chatbot')

    # Retrieve chat history from session or initialize it
    chat_history = request.session.get('chat_history', [])
    
    # We display results in a list to match the template's previous structure
    # but we store the full context for Gemini
    output_text = []

    if request.method == "POST":
        user_input = request.POST.get("user_input")
        
        # Add user message to history immediately
        chat_history.append({"role": "user", "text": user_input})
        request.session['chat_history'] = chat_history
        request.session.modified = True

        # Get API key from settings
        api_key = getattr(settings, "GEMINI_API_KEY", None)
        
        if not api_key:
            output_text = ["Error: GEMINI_API_KEY not found in settings. Please check your .env file and restart the server."]
            chat_history.append({"role": "model", "text": output_text[0]})
        else:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
            headers = {"Content-Type": "application/json"}

            # Build content with history for context
            contents = []
            # Use history excluding the very last message we just added
            for msg in chat_history[-11:-1]: 
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
                response = requests.post(url, json=payload, headers=headers, timeout=20)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Robust check for candidates and content
                    if 'candidates' in data and data['candidates']:
                        candidate = data['candidates'][0]
                        if 'content' in candidate and 'parts' in candidate['content']:
                            raw_text = candidate['content']['parts'][0].get('text', '')
                            
                            if raw_text:
                                # Update session history with model response
                                chat_history.append({"role": "model", "text": raw_text})
                                request.session['chat_history'] = chat_history
                                request.session.modified = True
                                output_text = raw_text.split("\n")
                            else:
                                err_msg = f"System: The AI returned an empty response. (Reason: {candidate.get('finishReason', 'Unknown')})"
                                chat_history.append({"role": "model", "text": err_msg})
                                output_text = [err_msg]
                        else:
                            # Handle cases like safety block
                            finish_reason = candidate.get('finishReason', 'Unknown')
                            err_msg = f"System: Response was blocked or empty. Reason: {finish_reason}"
                            chat_history.append({"role": "model", "text": err_msg})
                            output_text = [err_msg]
                    else:
                        err_msg = "System: No response candidates returned from the AI."
                        chat_history.append({"role": "model", "text": err_msg})
                        output_text = [err_msg]
                else:
                    try:
                        error_data = response.json()
                        error_message = error_data.get('error', {}).get('message', response.text)
                    except:
                        error_message = response.text
                    
                    err_msg = f"API Error ({response.status_code}): {error_message}"
                    chat_history.append({"role": "model", "text": err_msg})
                    output_text = [err_msg]
                    print(f"DEBUG: Gemini API Error: {response.status_code} - {response.text}")
            except requests.exceptions.Timeout:
                err_msg = "Connection Error: The request timed out. Please try again."
                chat_history.append({"role": "model", "text": err_msg})
                output_text = [err_msg]
            except requests.exceptions.RequestException as e:
                err_msg = f"Connection Error: {str(e)}"
                chat_history.append({"role": "model", "text": err_msg})
                output_text = [err_msg]

    return render(request, "chatbot.html", {
        "response": output_text,
        "chat_history": chat_history
    })

def index(request):
    return render(request, "index.html")