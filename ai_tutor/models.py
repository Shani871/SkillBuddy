from django.db import models
from django.conf import settings
from django.urls import reverse

class Roadmap(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="roadmaps")
    topic = models.CharField(max_length=255)
    roadmap_content = models.TextField()  # Markdown content
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Roadmap for {self.topic} (by {self.user.username})"

    def get_absolute_url(self):
        return reverse("roadmap_detail", kwargs={"pk": self.pk})

class ProjectIdea(models.Model):
    roadmap = models.ForeignKey(Roadmap, on_delete=models.CASCADE, related_name="project_ideas")
    title = models.CharField(max_length=255)
    description = models.TextField()
    difficulty = models.CharField(max_length=50, choices=[
        ('Beginner', 'Beginner'),
        ('Intermediate', 'Intermediate'),
        ('Advanced', 'Advanced'),
    ])

    def __str__(self):
        return self.title
