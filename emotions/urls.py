from django.urls import path
from . import views

urlpatterns = [
    path('capture/', views.capture_emotion, name='capture_emotion'),
    path('teacher-dashboard/', views.teacher_dashboard, name='teacher_dashboard'),
    path('parent-dashboard/', views.parent_dashboard, name='parent_dashboard'),
]
