from rest_framework import serializers
from accounts.models import User, Student
from course.models import Course, Program
from result.models import TakenCourse


class UserSerializer(serializers.ModelSerializer):
    role_label = serializers.CharField(source="get_user_role", read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "role",
            "role_label",
            "is_student",
            "is_lecturer",
            "is_superuser",
        ]


class StudentSerializer(serializers.ModelSerializer):
    student = UserSerializer(read_only=True)
    program_title = serializers.CharField(source="program.title", read_only=True)

    class Meta:
        model = Student
        fields = ["id", "student", "level", "program", "program_title"]


class ProgramSerializer(serializers.ModelSerializer):
    class Meta:
        model = Program
        fields = ["id", "title", "summary"]


class CourseSerializer(serializers.ModelSerializer):
    program_title = serializers.CharField(source="program.title", read_only=True)

    class Meta:
        model = Course
        fields = [
            "id",
            "title",
            "code",
            "credit",
            "summary",
            "level",
            "semester",
            "program",
            "program_title",
        ]


class TakenCourseSerializer(serializers.ModelSerializer):
    course = CourseSerializer(read_only=True)

    class Meta:
        model = TakenCourse
        fields = [
            "id",
            "student",
            "course",
            "assignment",
            "mid_exam",
            "quiz",
            "attendance",
            "final_exam",
            "total",
            "grade",
            "point",
            "comment",
        ]
