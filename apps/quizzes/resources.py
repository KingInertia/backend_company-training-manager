from django.conf import settings
from import_export import fields, resources
from import_export.widgets import ForeignKeyWidget

from apps.companies.models import Company

from .models import Quiz, QuizResult

User = settings.AUTH_USER_MODEL


class QuizResultResource(resources.ModelResource):
    company = fields.Field(
        column_name='company',
        attribute='quiz__company',
        widget=ForeignKeyWidget(Company, 'name')
    )
    user = fields.Field(
        column_name='user',
        attribute='user',
        widget=ForeignKeyWidget(User, 'username')
    )
    quiz = fields.Field(
        column_name='quiz',
        attribute='quiz',
        widget=ForeignKeyWidget(Quiz, 'title')
    )
    score = fields.Field(
        column_name='score'
    )
    date_passed = fields.Field(
        column_name='date passed',
        attribute='created_at'
    )

    class Meta:
        model = QuizResult
        fields = ('id', 'user', 'company', 'quiz', 'score', 'date_passed')
        export_order = ('id', 'user', 'company', 'quiz', 'score', 'date_passed')

    def dehydrate_score(self, quiz_result):
        return (quiz_result.correct_answers / quiz_result.total_questions) * 100
    
    def dehydrate_date_passed(self, quiz_result):
        return quiz_result.created_at.strftime('%Y-%m-%d %H:%M:%S')
