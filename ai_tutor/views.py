from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required

from .models import Roadmap, ProjectIdea
from .services import AIServiceError, generate_learning_roadmap

@login_required
def generate_roadmap_view(request):
    if request.method == "POST":
        topic = (request.POST.get("topic") or "").strip()
        if not topic:
            return render(request, "ai_tutor/roadmap_form.html", {"error": "Please provide a topic."})

        try:
            suggestion = generate_learning_roadmap(topic)
        except AIServiceError as exc:
            return render(request, "ai_tutor/roadmap_form.html", {"error": str(exc), "topic": topic})

        roadmap = Roadmap.objects.create(
            user=request.user,
            topic=topic,
            roadmap_content=suggestion.roadmap
        )

        for project in suggestion.projects:
            ProjectIdea.objects.create(
                roadmap=roadmap,
                title=project.title,
                description=project.description,
                difficulty=project.difficulty
            )

        return redirect('roadmap_detail', pk=roadmap.pk)

    return render(request, "ai_tutor/roadmap_form.html")

@login_required
def roadmap_detail_view(request, pk):
    roadmap = get_object_or_404(Roadmap, pk=pk, user=request.user)
    return render(request, "ai_tutor/roadmap_detail.html", {"roadmap": roadmap})

@login_required
def roadmap_list_view(request):
    roadmaps = Roadmap.objects.filter(user=request.user).order_by('-created_at')
    return render(request, "ai_tutor/roadmap_list.html", {"roadmaps": roadmaps})
