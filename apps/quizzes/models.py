from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.db import models

from apps.companies.models import Company
from tools.models import TimeStampedModel


class Quiz(TimeStampedModel):
    title = models.CharField(max_length=100)
    description = models.TextField()
    frequency_days = models.IntegerField(default=30)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='quizzes')


class Question(TimeStampedModel):
    quiz = models.ForeignKey(Quiz, related_name='questions', on_delete=models.CASCADE)
    text = models.TextField()
    answers = ArrayField(models.CharField(max_length=100))
    correct_answer = ArrayField(models.CharField(max_length=100))
    
    
class UserQuizPassing(models.Model):
    class Status(models.TextChoices):
        STARTED = 'started', 'Started'
        COMPLETED = 'completed', 'Completed'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='quizzes_passing'
    )
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.STARTED)
    start_test_time = models.DateTimeField(auto_now_add=True)
    end_test_time = models.DateTimeField(null=True, blank=True)
    
    
class QuizResult(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE)
    correct_answers = models.PositiveIntegerField()
    total_questions = models.PositiveIntegerField()
    test_time = models.DurationField() 
