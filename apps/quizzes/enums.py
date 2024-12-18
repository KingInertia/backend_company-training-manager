from enum import Enum


class FileType(Enum):
    CSV = 'csv'
    JSON = 'json'
    
    
class ScoresType(Enum):
    QUIZ = 'quiz'
    USER = 'user'