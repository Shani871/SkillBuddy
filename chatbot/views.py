import requests
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

def chatbot_view(request):
    output_text = []

    if request.method == "POST":
        user_input = request.POST.get("user_input")
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
        api_key = "AIzaSyDmZZR-GpCrnLjRz62PcxHqClsd1eWZffE"
        headers = {"Content-Type": "application/json"}

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": user_input}
                    ]
                }
            ]
        }

        response = requests.post(f"{url}?key={api_key}", json=payload, headers=headers)

        if response.status_code == 200:
            data = response.json()
            raw_text = data['candidates'][0]['content']['parts'][0]['text']
            output_text = raw_text.split("\n")  # Convert response into a list
        else:
            output_text = ["API request failed. Please try again."]

    return render(request, "chatbot.html", {"response": output_text})

def index(request):
    return render(request, "index.html")