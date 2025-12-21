import os
from unittest import mock
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()

class ChatbotViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.url = reverse('chatbot')

    def test_chatbot_view_requires_login(self):
        """Test that the chatbot view requires authentication."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    @mock.patch.dict(os.environ, {"GEMINI_API_KEY": ""})
    def test_chatbot_view_missing_api_key(self):
        """Test that the chatbot handles missing API key gracefully."""
        self.client.login(username='testuser', password='password123')
        response = self.client.post(self.url, {'user_input': 'Hello'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "GEMINI_API_KEY not found")

    def test_chatbot_view_get_request(self):
        """Test that a GET request loads the page correctly."""
        self.client.login(username='testuser', password='password123')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "chatbot.html")
