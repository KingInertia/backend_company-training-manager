from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.db.models import F, Max
from django.utils.timezone import now

from .models import Quiz, QuizResult

User = get_user_model()


@shared_task
def send_quiz_reminders():
    day_tyme = timedelta(days=1)

    expired_quizzes = Quiz.objects.filter(
        created_at__lte=now() - ((F('frequency_days')) * day_tyme)
    ).only('id', 'title', 'company', 'frequency_days').order_by('id')

    paginator = Paginator(expired_quizzes, 50)

    for page_num in paginator.page_range:
        page_quizzes = paginator.get_page(page_num)

        for quiz in page_quizzes:
            users = User.objects.filter(
                company_memberships__company=quiz.company
            )

            quiz_results = (
                QuizResult.objects.filter(user__in=users, quiz=quiz)
                .values('user')
                .annotate(last_completed=Max('created_at'))
                .order_by('user')
            )
            paginator = Paginator(quiz_results, 50)

            for page_num in paginator.page_range:
                page_results = paginator.get_page(page_num)
                result_map = {}
                
                for result in page_results:
                    result_map[result['user']] = result['last_completed']

                for user in users:
                    
                    last_result = result_map.get(user.id)

                    if not last_result or (now() - last_result).days > quiz.frequency_days:
                        send_mail(
                            subject=f'Quiz Reminder: {quiz.title}',
                            message=(
                                f'Hi {user.first_name},\n\n'
                                f'You have uncompleted quiz "{quiz.title}". '
                                f'Please complete it.'
                            ),
                            from_email=settings.EMAIL_HOST_USER,
                            recipient_list=[user.email],
                        )