from typing import Union

from django.db.models.query import QuerySet
from django.http import HttpResponse

from .enums import FileType
from .models import QuizResult
from .resources import QuizResultResource


def export_quiz_results(quiz_results: Union[QuerySet, list], file_type: FileType):
    result_data = QuizResultResource().export(quiz_results)

    if file_type == FileType.CSV:
        data = result_data.csv
        content_type = 'text/csv'
        type = FileType.CSV
    elif file_type == FileType.JSON:
        data = [result_data.dict]
        content_type = 'application/json'
        type = FileType.JSON
    else:
        raise ValueError("Unsupported type")

    response = HttpResponse(data, content_type=content_type)
    response['Content-Disposition'] = f'attachment; filename="results.{type}"'

    return response


def create_users_analytics(dynamic_scores_data: QuerySet[QuizResult]) -> list:
    dynamic_scores = {}

    for record in dynamic_scores_data:
        user_id = record['user__id']
        date = record['created_at']
        correct_answers = record['correct_answers']
        total_questions = record['total_questions']

        score = round((correct_answers / total_questions) * 100, 2)

        if user_id not in dynamic_scores:
            dynamic_scores[user_id] = {'scores': [], 'total_score': 0, 'count': 0}

        dynamic_scores[user_id]['total_score'] += score
        dynamic_scores[user_id]['count'] += 1
        
        average_score = round(dynamic_scores[user_id]['total_score'] / dynamic_scores[user_id]['count'], 2)
        dynamic_scores[user_id]['scores'].append({'date': date, 'score': average_score})

    response_data = []

    for user_id, user_data in dynamic_scores.items():
        response_data.append({'id': user_id, 'scores': user_data['scores']})

    return response_data


def create_quizzes_analytics(dynamic_scores_data: QuerySet[QuizResult]) -> list:
    quiz_scores = {}

    for record in dynamic_scores_data:
        quiz_id = record['quiz__id']
        date = record['created_at']
        correct_answers = record['correct_answers']
        total_questions = record['total_questions']

        score = round((correct_answers / total_questions) * 100, 2)

        if quiz_id not in quiz_scores:
            quiz_scores[quiz_id] = {'scores': [], 'total_score': 0, 'count': 0}

        quiz_scores[quiz_id]['total_score'] += score
        quiz_scores[quiz_id]['count'] += 1
        
        average_score = round(quiz_scores[quiz_id]['total_score'] / quiz_scores[quiz_id]['count'], 2)
        quiz_scores[quiz_id]['scores'].append({'date': date, 'score': average_score})

    response_data = []

    for quiz_id, quiz_data in quiz_scores.items():
        response_data.append({'id': quiz_id, 'scores': quiz_data['scores']})

    return response_data


def create_current_user_analytics(dynamic_scores_data: QuerySet[QuizResult]) -> list:
    user_scores = []
    total_score = 0
    count = 0

    for record in dynamic_scores_data:
        date = record['created_at']
        correct_answers = record['correct_answers']
        total_questions = record['total_questions']

        score = round((correct_answers / total_questions) * 100, 2)

        total_score += score
        count += 1

        average_score = round(total_score / count, 2)
        user_scores.append({'date': date, 'score': average_score})

    return user_scores