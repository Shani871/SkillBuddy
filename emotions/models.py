from django.db import models
from django.conf import settings
from accounts.models import Student

class EmotionRecord(models.Model):
    EMOTION_CHOICES = [
        ('Happy', 'Happy'),
        ('Neutral', 'Neutral'),
        ('Stressed', 'Stressed'),
        ('Sad', 'Sad'),
        ('Frustrated', 'Frustrated'),
        ('Tired', 'Tired'),
        ('Anxious', 'Anxious'),
    ]

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='emotion_records')
    timestamp = models.DateTimeField(auto_now_add=True)
    emotion = models.CharField(max_length=20, choices=EMOTION_CHOICES)
    confidence = models.FloatField(default=0.0)
    source = models.CharField(max_length=50, default='face') # face, text, voice

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.student} - {self.emotion} at {self.timestamp}"

class EmotionAlert(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='emotion_alerts')
    timestamp = models.DateTimeField(auto_now_add=True)
    message = models.TextField()
    is_for_teacher = models.BooleanField(default=True)
    is_for_parent = models.BooleanField(default=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"Alert for {self.student} - {self.timestamp}"
