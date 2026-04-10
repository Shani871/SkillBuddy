import requests
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.conf import settings
from .models import Roadmap, ProjectIdea

@login_required
def generate_roadmap_view(request):
    if request.method == "POST":
        topic = request.POST.get("topic")
        if not topic:
            return render(request, "ai_tutor/roadmap_form.html", {"error": "Please provide a topic."})

        api_key = getattr(settings, "GEMINI_API_KEY", None)
        if not api_key:
            return render(request, "ai_tutor/roadmap_form.html", {"error": "AI service is currently unavailable."})

        prompt = f"""
        Create a detailed study roadmap for the topic: {topic}.
        The roadmap should be structured in weeks or modules.
        Also, suggest 3 project ideas based on this topic with different difficulty levels (Beginner, Intermediate, Advanced).
        Format the output as a JSON object with the following keys:
        - "roadmap": "Markdown formatted string"
        - "projects": [
            {{"title": "...", "description": "...", "difficulty": "..."}},
            ...
        ]
        Only return the JSON object.
        """

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "response_mime_type": "application/json",
            }
        }

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            if response.status_code == 200:
                data = response.json()
                content = data['candidates'][0]['content']['parts'][0]['text']
                import json
                ai_data = json.loads(content)
                
                # Create Roadmap object
                roadmap = Roadmap.objects.create(
                    user=request.user,
                    topic=topic,
                    roadmap_content=ai_data.get('roadmap', '')
                )
                
                # Create ProjectIdea objects
                for project in ai_data.get('projects', []):
                    ProjectIdea.objects.create(
                        roadmap=roadmap,
                        title=project.get('title', 'Idea'),
                        description=project.get('description', ''),
                        difficulty=project.get('difficulty', 'Beginner')
                    )
                
                return redirect('roadmap_detail', pk=roadmap.pk)
            else:
                error_msg = response.text
                try:
                    error_data = response.json()
                    error_msg = error_data.get('error', {}).get('message', response.text)
                except:
                    pass
                return render(request, "ai_tutor/roadmap_form.html", {"error": f"API Error ({response.status_code}): {error_msg}"})
        except Exception as e:
            return render(request, "ai_tutor/roadmap_form.html", {"error": f"Error: {str(e)}"})

    return render(request, "ai_tutor/roadmap_form.html")

@login_required
def roadmap_detail_view(request, pk):
    roadmap = get_object_or_404(Roadmap, pk=pk, user=request.user)
    return render(request, "ai_tutor/roadmap_detail.html", {"roadmap": roadmap})

@login_required
def roadmap_list_view(request):
    roadmaps = Roadmap.objects.filter(user=request.user).order_by('-created_at')
    return render(request, "ai_tutor/roadmap_list.html", {"roadmaps": roadmaps})
