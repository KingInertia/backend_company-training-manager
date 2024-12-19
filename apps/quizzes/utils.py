from typing import Union

from django.db.models.query import QuerySet
from django.http import HttpResponse

from .enums import FileType, ScoreIdType
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


def create_users_analytics(dynamic_scores_data: QuerySet[QuizResult], id_type: ScoreIdType) -> list:
    dynamic_scores = {}

    for record in dynamic_scores_data:
        group_id = record[id_type.value]
        date = record['created_at']
        correct_answers = record['correct_answers']
        total_questions = record['total_questions']

        score = round((correct_answers / total_questions) * 100, 2)

        if group_id not in dynamic_scores:
            dynamic_scores[group_id] = {'scores': [], 'total_score': 0, 'count': 0}

        dynamic_scores[group_id]['total_score'] += score
        dynamic_scores[group_id]['count'] += 1

        average_score = round(dynamic_scores[group_id]['total_score'] / dynamic_scores[group_id]['count'], 2)
        dynamic_scores[group_id]['scores'].append({'date': date, 'score': average_score})

    response_data = []

    for group_id, group_data in dynamic_scores.items():
        response_data.append({'id': group_id, 'scores': group_data['scores']})

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