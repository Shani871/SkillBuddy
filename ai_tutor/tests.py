from unittest import mock

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from .models import Roadmap
from .services import ProjectSuggestion, RoadmapSuggestion, parse_roadmap_response

User = get_user_model()


class RoadmapResponseParserTests(SimpleTestCase):
    def test_parse_roadmap_response_accepts_json_code_fence(self):
        suggestion = parse_roadmap_response(
            """```json
            {
              "roadmap": "# Python Basics\\nPractice every week.",
              "projects": [
                {
                  "title": "CLI Calculator",
                  "description": "Build a small calculator.",
                  "difficulty": "Beginner"
                }
              ]
            }
            ```"""
        )

        self.assertIn("Python Basics", suggestion.roadmap)
        self.assertEqual(len(suggestion.projects), 1)
        self.assertEqual(suggestion.projects[0].title, "CLI Calculator")


class RoadmapViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="learner", password="password123")
        self.client.login(username="learner", password="password123")

    @mock.patch("ai_tutor.views.generate_learning_roadmap")
    def test_generate_roadmap_creates_saved_ai_plan(self, mock_generate):
        mock_generate.return_value = RoadmapSuggestion(
            roadmap="# Django Roadmap",
            projects=[
                ProjectSuggestion(
                    title="Course Tracker",
                    description="Build a simple course tracker.",
                    difficulty="Beginner",
                )
            ],
        )

        response = self.client.post(reverse("generate_roadmap"), {"topic": "Django"})

        roadmap = Roadmap.objects.get()
        self.assertRedirects(response, reverse("roadmap_detail", kwargs={"pk": roadmap.pk}))
        self.assertEqual(roadmap.topic, "Django")
        self.assertEqual(roadmap.project_ideas.count(), 1)

    def test_generate_roadmap_requires_topic(self):
        response = self.client.post(reverse("generate_roadmap"), {"topic": ""})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Please provide a topic.")
