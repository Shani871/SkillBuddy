from django.contrib import admin

from .models import ProjectIdea, Roadmap


class ProjectIdeaInline(admin.TabularInline):
    model = ProjectIdea
    extra = 0


@admin.register(Roadmap)
class RoadmapAdmin(admin.ModelAdmin):
    list_display = ("topic", "user", "created_at")
    list_filter = ("created_at",)
    search_fields = ("topic", "user__username", "user__email")
    inlines = (ProjectIdeaInline,)


@admin.register(ProjectIdea)
class ProjectIdeaAdmin(admin.ModelAdmin):
    list_display = ("title", "difficulty", "roadmap")
    list_filter = ("difficulty",)
    search_fields = ("title", "description", "roadmap__topic")
