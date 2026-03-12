from django.conf import settings
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import User
from course.models import Course, Program
from quiz.models import Choice, MCQuestion, Quiz, Sitting


@override_settings(
    STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage",
    LANGUAGE_CODE="en",
)
class QuizEngineTests(TestCase):
    def setUp(self):
        self.program = Program.objects.create(title="Engineering")
        self.course = Course.objects.create(
            title="Software Engineering",
            code="ENG301",
            credit=3,
            summary="SE",
            program=self.program,
            level=settings.BACHELOR_DEGREE,
            year=3,
            semester=settings.FIRST,
        )

        self.student = User.objects.create_user(
            username="student_user",
            password="password",
            is_student=True,
        )

    def _create_quiz(self, title, **kwargs):
        question_count = kwargs.pop("question_count", 3)
        quiz = Quiz.objects.create(course=self.course, title=title, **kwargs)

        for idx in range(question_count):
            question = MCQuestion.objects.create(content=f"Question {idx + 1}")
            question.quiz.add(quiz)
            Choice.objects.create(question=question, choice_text="Correct", correct=True)
            Choice.objects.create(question=question, choice_text="Wrong", correct=False)

        return quiz

    def _question_order(self, quiz):
        ids = list(quiz.question_set.values_list("id", flat=True))
        return ",".join(str(qid) for qid in ids) + ","

    def test_single_attempt_quiz_cannot_be_taken_twice(self):
        quiz = self._create_quiz("Single Attempt Quiz", single_attempt=True)
        first = Sitting.objects.new_sitting(self.student, quiz, self.course)
        first.mark_quiz_complete()

        second = Sitting.objects.user_sitting(self.student, quiz, self.course)
        self.assertFalse(second)

    def test_random_order_quiz_varies_question_order(self):
        quiz = self._create_quiz("Random Quiz", random_order=True, question_count=6)

        orders = set()
        for _ in range(7):
            sitting = Sitting.objects.new_sitting(self.student, quiz, self.course)
            orders.add(sitting.question_order)
            sitting.delete()

        self.assertGreater(len(orders), 1)

    def test_score_above_pass_mark_is_passed(self):
        quiz = self._create_quiz("Pass Quiz", pass_mark=60, question_count=5)
        order = self._question_order(quiz)

        sitting = Sitting.objects.create(
            user=self.student,
            quiz=quiz,
            course=self.course,
            question_order=order,
            question_list="",
            incorrect_questions="",
            current_score=4,
            complete=True,
            user_answers="{}",
        )

        self.assertTrue(sitting.check_if_passed)

    def test_score_below_pass_mark_is_failed(self):
        quiz = self._create_quiz("Fail Quiz", pass_mark=70, question_count=5)
        order = self._question_order(quiz)

        sitting = Sitting.objects.create(
            user=self.student,
            quiz=quiz,
            course=self.course,
            question_order=order,
            question_list="",
            incorrect_questions="",
            current_score=2,
            complete=True,
            user_answers="{}",
        )

        self.assertFalse(sitting.check_if_passed)

    def test_draft_quiz_not_visible_to_student(self):
        Quiz.objects.create(course=self.course, title="Draft Quiz", draft=True)
        Quiz.objects.create(course=self.course, title="Live Quiz", draft=False)

        self.client.force_login(self.student)
        response = self.client.get(reverse("quiz_index", kwargs={"slug": self.course.slug}))

        self.assertEqual(response.status_code, 200)
        quiz_titles = list(response.context["quizzes"].values_list("title", flat=True))
        self.assertIn("Live Quiz", quiz_titles)
        self.assertNotIn("Draft Quiz", quiz_titles)

    def test_submitting_quiz_with_missing_answers_is_handled(self):
        quiz = self._create_quiz("Question Quiz", draft=False, question_count=1)

        self.client.force_login(self.student)
        response = self.client.post(
            reverse("quiz_take", kwargs={"pk": self.course.pk, "slug": quiz.slug}),
            data={},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors)
