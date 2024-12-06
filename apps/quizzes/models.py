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
    
