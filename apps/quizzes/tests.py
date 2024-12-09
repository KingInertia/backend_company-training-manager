from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.companies.models import Company, CompanyMember

from .models import Question, Quiz

User = get_user_model()

class QuizUpdateTestCase(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="admin",
            password="1Q_az_2wsx_3edc",
            email="owner@example.com"
        )
        
        self.company = Company.objects.create(
            name="name", 
            description="description", 
            owner=self.user
            )
        
        CompanyMember.objects.create(user=self.user, company=self.company, role=CompanyMember.Role.ADMIN)

        self.quiz = Quiz.objects.create(
            title="title1",
            description="description",
            frequency_days=1,
            company=self.company
        )

        self.question1 = Question.objects.create(
            quiz=self.quiz,
            text="text",
            answers=["answers4", "answers5", "answers6"],
            correct_answer=["answers6", "answers4"]
        )

        self.question2 = Question.objects.create(
            quiz=self.quiz,
            text="text4",
            answers=["answers1", "answers2", "answers3"],
            correct_answer=["answers1"]
        )


    def test_update_quiz_success(self):
        self.client.force_authenticate(user=self.user)

        updated_data = {
            "title": "new title",
            "description": "description",
            "frequency_days": 30,
            "questions": [
                {
                    "id": self.question1.id,
                    "text": "Updated Question 1",
                    "answers": ["answers333", "answers111", "answers222"],
                    "correct_answer": ["answers333"]
                },
                {   
                    "text": "New Question",
                    "answers": ["answers1", "answers2", "answers3"],
                    "correct_answer": ["answers3"]
                }
            ]
        }
        
        response = self.client.patch(f'/api/v1/quizzes/{self.quiz.id}/', updated_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.quiz.refresh_from_db()
        self.assertEqual(self.quiz.title, "new title")
        self.assertEqual(self.quiz.questions.count(), 2)
        
        questions = self.quiz.questions.all()
        
        updated_question1 = questions.get(id=self.question1.id)
        self.assertEqual(updated_question1.text, "Updated Question 1")
        self.assertEqual(updated_question1.answers, ["answers333", "answers111", "answers222"])
        self.assertEqual(updated_question1.correct_answer, ["answers333"])
        
        new_question = questions.exclude(id=self.question1.id).first()
        self.assertEqual(new_question.text, "New Question")
        self.assertEqual(new_question.answers, ["answers1", "answers2", "answers3"])
        self.assertEqual(new_question.correct_answer, ["answers3"])
        
        assert not Question.objects.filter(id=self.question2.id).exists()


    def test_create_quiz_success(self):
        self.client.force_authenticate(user=self.user)

        create_data = {
            "title": "new title",
            "description": "description",
            "frequency_days": 30,
            "company": self.company.id,
            "questions": [
                {
                    "text": "Question 1",
                    "answers": ["answers333", "answers111", "answers222"],
                    "correct_answer": ["answers333"]
                },
                {   
                    "text": "New Question",
                    "answers": ["answers1", "answers2", "answers3"],
                    "correct_answer": ["answers3"]
                }
            ]
        }

        response = self.client.post('/api/v1/quizzes/', create_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        quiz = Quiz.objects.last()
        self.assertEqual(quiz.questions.count(), 2)
        question = quiz.questions.get(text="Question 1")
        self.assertEqual(question.answers, ["answers333", "answers111", "answers222"])
        self.assertEqual(question.correct_answer, ["answers333"])
        question2 = quiz.questions.get(text="New Question")
        self.assertEqual(question2.answers, ["answers1", "answers2", "answers3"])
        self.assertEqual(question2.correct_answer, ["answers3"])