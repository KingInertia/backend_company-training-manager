from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.db.models import F
from django.utils.timezone import now

from ..companies.models import CompanyMember
from .models import Quiz, QuizResult


@shared_task
def send_quiz_reminders():
    
    day_tyme = timedelta(days=1)

    expired_quizzes = Quiz.objects.filter(
        created_at__lte=now() - ((F('frequency_days')) * day_tyme)
    ).only('id', 'title', 'company')

    for quiz in expired_quizzes:
        members = CompanyMember.objects.filter(company=quiz.company).select_related('user')

        for member in members:
            has_result = QuizResult.objects.filter(user=member.user, quiz=quiz).exists()

            if not has_result:
                send_mail(
                    subject=f'Quiz Reminder: {quiz.title}',
                    message=(
                    f'Hi {member.user.first_name},\n\n'
                    f'You have uncompleted quiz "{quiz.title}". '
                    f'Please complete it.'
                    ),
                    from_email=settings.EMAIL_HOST_USER,
                    recipient_list=[member.user.email],
                )
