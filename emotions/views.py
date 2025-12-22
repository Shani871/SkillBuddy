import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from accounts.models import Student
from .models import EmotionRecord
from .services import EmotionAnalysisService

@csrf_exempt
def capture_emotion(request):
    """
    Endpoint to receive image data from the login page and record emotion.
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            image_data = data.get('image')
            username = data.get('username')
            
            # Find the student
            student = Student.objects.filter(student__username=username).first()
            if not student:
                 return JsonResponse({'status': 'error', 'message': 'Student not found'}, status=404)

            # Analyze emotion
            emotion_label, confidence = EmotionAnalysisService.detect_face_emotion(image_data)
            
            # Record the emotion
            EmotionRecord.objects.create(
                student=student,
                emotion=emotion_label,
                confidence=confidence,
                source='face'
            )
            
            # Check for alerts
            EmotionAnalysisService.create_alerts_if_needed(student)
            
            return JsonResponse({
                'status': 'success',
                'emotion': emotion_label,
                'confidence': confidence
            })
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)

@login_required
def teacher_dashboard(request):
    """
    View for teachers to see emotional trends of their students.
    """
    if not request.user.is_lecturer and not request.user.is_superuser:
        return JsonResponse({'status': 'error', 'message': 'Access denied'}, status=403)
    
    recent_records = EmotionRecord.objects.all()[:50]
    alerts = EmotionAlert.objects.filter(is_for_teacher=True, is_read=False)[:10]
    
    return render(request, "emotions/teacher_dashboard.html", {
        "recent_records": recent_records,
        "alerts": alerts
    })

@login_required
def parent_dashboard(request):
    """
    View for parents to see emotional summary of their child.
    """
    if not request.user.is_parent:
        return JsonResponse({'status': 'error', 'message': 'Access denied'}, status=403)
    
    parent = request.user.parent
    student = parent.student
    
    latest_record = EmotionRecord.objects.filter(student=student).first()
    alerts = EmotionAlert.objects.filter(student=student, is_for_parent=True, is_read=False)
    
    return render(request, "emotions/parent_dashboard.html", {
        "student": student,
        "latest_record": latest_record,
        "alerts": alerts
    })
