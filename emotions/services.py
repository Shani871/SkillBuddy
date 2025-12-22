import os
import base64
import numpy as np
import cv2
from django.conf import settings
from .models import EmotionRecord, EmotionAlert

class EmotionAnalysisService:
    @staticmethod
    def detect_face_emotion(image_data_base64):
        """
        Analyzes facial expression from base64 image data.
        Returns (emotion_label, confidence)
        """
        try:
            # Decode image
            format, imgstr = image_data_base64.split(';base64,')
            ext = format.split('/')[-1]
            data = base64.b64decode(imgstr)
            
            # Convert to numpy array for OpenCV/MediaPipe
            nparr = np.frombuffer(data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            # Placeholder logic: In a real implementation, we would use
            # a pre-trained Keras/TensorFlow model or MediaPipe here.
            # For now, we return 'Neutral' as a placeholder.
            # TODO: Integrate pre-trained CNN model
            
            return "Neutral", 0.8
        except Exception as e:
            print(f"Error in face emotion detection: {e}")
            return "Neutral", 0.0

    @staticmethod
    def detect_text_sentiment(text):
        """
        Analyzes sentiment from text input.
        Returns (emotion_label, confidence)
        """
        # Placeholder for NLP sentiment analysis
        return "Neutral", 1.0

    @staticmethod
    def calculate_fused_emotion(face_data=None, text_data=None, voice_data=None):
        """
        Weighted fusion of different emotion sources.
        """
        # Weights: Face (60%), Text (20%), Voice (20%)
        # Current implementation only uses face data for login
        if face_data:
            return face_data[0], face_data[1]
        return "Neutral", 1.0

    @staticmethod
    def create_alerts_if_needed(student):
        """
        Checks recent emotion history and generates alerts for teachers/parents
        if negative trends are detected (e.g., 3 days of stress).
        """
        recent_records = EmotionRecord.objects.filter(student=student)[:3]
        if len(recent_records) >= 3:
            stressed_count = sum(1 for r in recent_records if r.emotion in ['Stressed', 'Sad', 'Anxious'])
            if stressed_count >= 3:
                EmotionAlert.objects.get_or_create(
                    student=student,
                    message=f"Student {student} has appeared stressed for 3 consecutive logins. Consider checking in.",
                    is_for_teacher=True,
                    is_for_parent=True,
                    is_read=False
                )
