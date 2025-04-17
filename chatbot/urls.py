from django.urls import path
from . import views


urlpatterns = [
   path('sk/', views.chatbot_view, name='chatbot'),
   path('index/', views.index, name='index'),
]
