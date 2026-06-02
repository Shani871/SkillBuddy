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

    @mock.patch("chatbot.views.generate_chat_reply")
    def test_chatbot_view_ai_service_error(self, mock_generate):
        """Test that the chatbot handles missing API key gracefully."""
        from ai_tutor.services import AIServiceError

        mock_generate.side_effect = AIServiceError("AI service is not configured.")
        self.client.login(username='testuser', password='password123')
        response = self.client.post(self.url, {'user_input': 'Hello'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "AI service is not configured.")

    @mock.patch("chatbot.views.generate_chat_reply")
    def test_chatbot_view_stores_ai_reply_in_session(self, mock_generate):
        mock_generate.return_value = "Practice one concept at a time."
        self.client.login(username='testuser', password='password123')

        response = self.client.post(self.url, {'user_input': 'How should I study?'})

        self.assertEqual(response.status_code, 200)
        history = self.client.session["chat_history"]
        self.assertEqual(history[-2]["role"], "user")
        self.assertEqual(history[-1]["text"], "Practice one concept at a time.")

    def test_chatbot_view_get_request(self):
        """Test that a GET request loads the page correctly."""
        self.client.login(username='testuser', password='password123')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "chatbot.html")
