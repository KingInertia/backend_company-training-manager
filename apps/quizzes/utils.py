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