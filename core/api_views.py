import logging
from django.contrib.auth import authenticate
from django.db.models import Q, Sum
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import Student, User
from course.models import Course
from emotions.services import EmotionAnalysisService
from result.models import TakenCourse, CourseAttendance, Result
from ai_tutor.services import AIServiceError, generate_chat_reply
from .serializers import UserSerializer, CourseSerializer, TakenCourseSerializer

logger = logging.getLogger(__name__)


@api_view(["POST"])
@permission_classes([AllowAny])
def login_api(request):
    """Authenticate user and return JWT tokens along with user info."""
    username = request.data.get("username")
    password = request.data.get("password")

    user = authenticate(username=username, password=password)
    if user is not None:
        if getattr(user, "login_disabled", False):
            return Response(
                {"detail": "Your login has been disabled by an administrator."},
                status=status.HTTP_403_FORBIDDEN,
            )

        refresh = RefreshToken.for_user(user)
        student_data = None
        if user.is_student:
            student = Student.objects.filter(student=user).first()
            if student:
                student_data = {
                    "id": student.id,
                    "level": student.level,
                    "program": student.program.title if student.program else "",
                }

        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": UserSerializer(user).data,
                "student": student_data,
            },
            status=status.HTTP_200_OK,
        )

    return Response(
        {"detail": "Invalid username or password credentials."},
        status=status.HTTP_400_BAD_REQUEST,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard_metrics_api(request):
    """Get metrics and recent activity for the user's role workspace."""
    user = request.user
    role = user.effective_role

    # Default metrics
    students_count = User.objects.filter(is_student=True).count()
    faculty_count = User.objects.filter(is_lecturer=True).count()
    courses_count = Course.objects.count()

    # Simple JSON representation for dashboard charts
    chart_data = [
        {"name": "Students", "count": students_count},
        {"name": "Faculty", "count": faculty_count},
        {"name": "Courses", "count": courses_count},
    ]

    return Response(
        {
            "role": role,
            "metrics": {
                "total_students": students_count,
                "total_faculty": faculty_count,
                "total_courses": courses_count,
            },
            "chart_data": chart_data,
        },
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def chatbot_api(request):
    """Generate tutor chat response from Gemini API using context history."""
    user_input = request.data.get("message", "").strip()
    history = request.data.get("history", [])

    if not user_input:
        return Response(
            {"detail": "Message input is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Compile user details, multi-tenant college context, and academic scores
    user = request.user
    system_context = ""

    system_context += "User profile:\n"
    system_context += f"- Username: {user.username}\n"
    system_context += f"- Full Name: {user.get_full_name}\n"
    system_context += f"- Email: {user.email or 'N/A'}\n"
    system_context += f"- Role: {user.get_user_role}\n"
    if user.college:
        system_context += f"- College Tenant: {user.college.name} (Code: {user.college.code}, Domain: {user.college.domain})\n"
    if user.department_name:
        system_context += f"- Department: {user.department_name}\n"

    student = Student.objects.filter(student=user).first()
    if student:
        system_context += f"\nStudent Academics:\n"
        system_context += f"- Program: {student.program.title if student.program else 'N/A'}\n"
        system_context += f"- Level: {student.level or 'N/A'}\n"

        taken_courses = TakenCourse.objects.filter(student=student)
        if taken_courses.exists():
            system_context += "\nEnrolled Courses, Grades & Score breakdown:\n"
            for tc in taken_courses:
                system_context += f"- {tc.course.title} ({tc.course.code}):\n"
                system_context += f"  * Credits: {tc.course.credit}\n"
                system_context += f"  * Semester: {tc.course.semester}\n"
                system_context += f"  * Marks: Assignment={tc.assignment}, Mid Exam={tc.mid_exam}, Quiz={tc.quiz}, Attendance={tc.attendance}, Final Exam={tc.final_exam}\n"
                system_context += f"  * Total: {tc.total}/100\n"
                system_context += f"  * Grade: {tc.grade or 'N/A'}\n"
                system_context += f"  * Status: {tc.comment or 'N/A'}\n"

                # Check for attendance summary
                if hasattr(tc, "attendance_summary"):
                    att = tc.attendance_summary
                    system_context += f"  * Attendance: {att.classes_attended} classes attended out of {att.total_classes} total classes ({att.percentage}%)\n"
                    if att.is_below_required:
                        system_context += "    (Warning: Attendance is below required 75% threshold)\n"

            try:
                gpa = taken_courses.first().calculate_gpa()
                cgpa = taken_courses.first().calculate_cgpa()
                system_context += f"\nGPA Summary:\n"
                system_context += f"- Current Semester GPA: {gpa}\n"
                system_context += f"- Cumulative GPA (CGPA): {cgpa}\n"
            except Exception:
                pass

    try:
        reply = generate_chat_reply(history, user_input, system_context=system_context)
        return Response({"reply": reply}, status=status.HTTP_200_OK)
    except AIServiceError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def student_courses_api(request):
    """Get registered and available registration courses for the student."""
    user = request.user
    if not user.is_student:
        return Response(
            {"detail": "Only student accounts have access to this resource."},
            status=status.HTTP_403_FORBIDDEN,
        )

    student = Student.objects.filter(student=user).first()
    if not student:
        return Response(
            {"detail": "Student profile not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    registered_taken = TakenCourse.objects.filter(student=student)
    registered_ids = registered_taken.values_list("course_id", flat=True)

    available_courses = Course.objects.filter(
        program=student.program, level=student.level
    ).exclude(id__in=registered_ids)

    return Response(
        {
            "registered": TakenCourseSerializer(registered_taken, many=True).data,
            "available": CourseSerializer(available_courses, many=True).data,
        },
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def register_course_api(request):
    """Enroll the student in a specified course."""
    user = request.user
    if not user.is_student:
        return Response(
            {"detail": "Only student accounts can enroll in courses."},
            status=status.HTTP_403_FORBIDDEN,
        )

    student = Student.objects.filter(student=user).first()
    course_id = request.data.get("course_id")

    try:
        course = Course.objects.get(pk=course_id)
    except Course.DoesNotExist:
        return Response(
            {"detail": "Specified course does not exist."},
            status=status.HTTP_404_NOT_FOUND,
        )

    if TakenCourse.objects.filter(student=student, course=course).exists():
        return Response(
            {"detail": "Already enrolled in this course."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    obj = TakenCourse.objects.create(student=student, course=course)
    obj.save()

    return Response(
        {
            "detail": f"Successfully enrolled in {course.title}.",
            "taken_course": TakenCourseSerializer(obj).data,
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def capture_emotion_api(request):
    """Receive base64 camera image data and record student emotion status."""
    user = request.user
    student = Student.objects.filter(student=user).first()
    if not student:
        return Response(
            {"detail": "Only student accounts can submit emotion tracking logs."},
            status=status.HTTP_403_FORBIDDEN,
        )

    image_data = request.data.get("image")
    if not image_data:
        return Response(
            {"detail": "No image data was provided."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        # Fallback to sync run analysis
        record = EmotionAnalysisService.analyze_and_store_emotion(
            student, image_data
        )
        return Response(
            {
                "status": "success",
                "emotion": record.emotion,
                "confidence": record.confidence,
            },
            status=status.HTTP_200_OK,
        )
    except Exception as exc:
        logger.exception("Emotion capture failed: %s", exc)
        return Response(
            {"detail": "Unable to process emotion image logs."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
