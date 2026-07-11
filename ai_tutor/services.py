import json
import logging
from dataclasses import dataclass

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class AIServiceError(Exception):
    """Raised when the AI provider cannot return a usable response."""


@dataclass
class ProjectSuggestion:
    title: str
    description: str
    difficulty: str


@dataclass
class RoadmapSuggestion:
    roadmap: str
    projects: list[ProjectSuggestion]


class GeminiClient:
    def __init__(self, api_key=None, model=None, timeout=30):
        self.api_key = api_key if api_key is not None else getattr(settings, "GEMINI_API_KEY", "")
        self.model = model or getattr(settings, "GEMINI_MODEL", "gemini-2.0-flash")
        self.timeout = timeout

    @property
    def is_configured(self):
        return bool(self.api_key)

    @property
    def endpoint(self):
        return (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent?key={self.api_key}"
        )

    def generate_content(self, contents, generation_config=None):
        if not self.is_configured:
            raise AIServiceError("AI service is not configured. Add GEMINI_API_KEY to your environment.")

        payload = {"contents": contents}
        if generation_config:
            payload["generationConfig"] = generation_config

        try:
            response = requests.post(
                self.endpoint,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=self.timeout,
            )
        except requests.exceptions.Timeout as exc:
            raise AIServiceError("The AI request timed out. Please try again.") from exc
        except requests.exceptions.RequestException as exc:
            raise AIServiceError("The AI service could not be reached. Please try again.") from exc

        if response.status_code != 200:
            message = response.text
            try:
                message = response.json().get("error", {}).get("message", message)
            except ValueError:
                pass
            logger.error("Gemini API error %s: %s", response.status_code, response.text)
            raise AIServiceError(f"AI service error ({response.status_code}): {message}")

        try:
            data = response.json()
            candidate = data["candidates"][0]
            text = candidate["content"]["parts"][0].get("text", "").strip()
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise AIServiceError("The AI service returned an unexpected response.") from exc

        if not text:
            finish_reason = candidate.get("finishReason", "unknown")
            raise AIServiceError(f"The AI service returned an empty response ({finish_reason}).")

        return text


def build_chat_contents(chat_history, user_input, max_history=10, system_context=None):
    system_text = (
        "You are SkillBuddy AI Assistant, a friendly academic tutor. "
        "Answer clearly, keep students focused, and avoid inventing details "
        "about their account or courses unless they provide them."
    )
    if system_context:
        system_text += f"\n\nHere is verified information about the current user, their academics, and their college:\n{system_context}"

    contents = [
        {
            "role": "user",
            "parts": [
                {
                    "text": system_text
                }
            ],
        },
        {
            "role": "model",
            "parts": [{"text": "Understood. I will help as a clear and practical tutor using the provided context."}],
        },
    ]

    for message in chat_history[-max_history:]:
        text = (message.get("text") or "").strip()
        if not text:
            continue
        contents.append(
            {
                "role": "model" if message.get("role") == "model" else "user",
                "parts": [{"text": text}],
            }
        )

    contents.append({"role": "user", "parts": [{"text": user_input}]})
    return contents


def generate_chat_reply(chat_history, user_input, system_context=None):
    client = GeminiClient(timeout=20)
    contents = build_chat_contents(chat_history, user_input, system_context=system_context)
    return client.generate_content(contents)


def generate_learning_roadmap(topic):
    prompt = f"""
Create a detailed study roadmap for: {topic}

Return only a JSON object with this exact shape:
{{
  "roadmap": "Markdown formatted roadmap organized by weeks or modules",
  "projects": [
    {{"title": "...", "description": "...", "difficulty": "Beginner"}},
    {{"title": "...", "description": "...", "difficulty": "Intermediate"}},
    {{"title": "...", "description": "...", "difficulty": "Advanced"}}
  ]
}}

Keep the roadmap practical for a learner and include checkpoints, practice tasks, and resources to review.
"""
    client = GeminiClient(timeout=30)
    response_text = client.generate_content(
        [{"role": "user", "parts": [{"text": prompt}]}],
        generation_config={"response_mime_type": "application/json"},
    )
    return parse_roadmap_response(response_text)


def parse_roadmap_response(response_text):
    try:
        data = json.loads(_extract_json(response_text))
    except (TypeError, ValueError) as exc:
        raise AIServiceError("The AI service returned roadmap data that could not be read.") from exc

    roadmap = str(data.get("roadmap", "")).strip()
    if not roadmap:
        raise AIServiceError("The AI service returned an empty roadmap.")

    projects = []
    for project in data.get("projects", [])[:3]:
        title = str(project.get("title", "Project idea")).strip() or "Project idea"
        description = str(project.get("description", "")).strip()
        difficulty = str(project.get("difficulty", "Beginner")).strip()
        if difficulty not in {"Beginner", "Intermediate", "Advanced"}:
            difficulty = "Beginner"
        projects.append(ProjectSuggestion(title, description, difficulty))

    return RoadmapSuggestion(roadmap=roadmap, projects=projects)


def _extract_json(text):
    text = (text or "").strip()
    if text.startswith("```"):
        text = text.strip("`").strip()
        if text.lower().startswith("json"):
            text = text[4:].strip()

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end >= start:
        return text[start : end + 1]
    return text
