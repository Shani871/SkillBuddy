from django.urls import path
from . import views

urlpatterns = [
    path('generate/', views.generate_roadmap_view, name='generate_roadmap'),
    path('roadmap/<int:pk>/', views.roadmap_detail_view, name='roadmap_detail'),
    path('roadmaps/', views.roadmap_list_view, name='roadmap_list'),
]
