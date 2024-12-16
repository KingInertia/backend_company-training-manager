from enum import Enum
from typing import Union

from django.db.models.query import QuerySet
from django.http import HttpResponse

from .resources import QuizResultResource


class FileType(Enum):
    CSV = 'csv'
    JSON = 'json'
    
    
class FilterType(Enum):
    QUIZ = 'quiz'
    USER = 'user'


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


def create_analitycs_data(dynamic_scores_data: Union[QuerySet], filter_by: FilterType):
    dynamic_scores = []
    id_changed = None
    index = -1
    filter_by = filter_by.value
    
    for record in dynamic_scores_data:
        id = record[filter_by]
        day = record['day']
        total_correct_answers = record['total_correct_answers']
        total_total_questions = record['total_total_questions']
        score = round(total_correct_answers / total_total_questions, 2) * 100
            
        if id != id_changed:
            dynamic_scores.append({'id': id, 'dynamic_time': []})
            id_changed = id
            index += 1
        
        dynamic_scores[index]['dynamic_time'].append({'day': day, 'average_score': score})
    
    return dynamic_scores