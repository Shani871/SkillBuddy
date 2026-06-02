import logging
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from ai_tutor.services import AIServiceError, generate_chat_reply

logger = logging.getLogger(__name__)

@login_required
def chatbot_view(request):
    if request.GET.get('clear') == '1':
        request.session['chat_history'] = []
        request.session.modified = True
        return redirect('chatbot')

    # Retrieve chat history from session or initialize it
    chat_history = request.session.get('chat_history', [])
    
    output_text = []

    if request.method == "POST":
        user_input = (request.POST.get("user_input") or "").strip()
        if not user_input:
            return render(request, "chatbot.html", {
                "response": ["Please enter a question."],
                "chat_history": chat_history
            })

        previous_history = list(chat_history)
        chat_history.append({"role": "user", "text": user_input})
        request.session['chat_history'] = chat_history
        request.session.modified = True

        try:
            reply = generate_chat_reply(previous_history, user_input)
        except AIServiceError as exc:
            reply = f"Error: {exc}"
            logger.warning("AI chat failed: %s", exc)

        chat_history.append({"role": "model", "text": reply})
        request.session['chat_history'] = chat_history
        request.session.modified = True
        output_text = reply.split("\n")

    return render(request, "chatbot.html", {
        "response": output_text,
        "chat_history": chat_history
    })

def index(request):
    return render(request, "index.html")
