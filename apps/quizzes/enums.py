from enum import Enum


class FileType(Enum):
    CSV = 'csv'
    JSON = 'json'


class ScoreIdType(Enum):
    USER = "user__id"
    QUIZ = "quiz__id"