from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.companies.models import Company, CompanyMember

from .models import Question, Quiz, QuizResult, UserQuizSession

User = get_user_model()


class QuizTestCase(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="admin",
            password="1Q_az_2wsx_3edc",
            email="owner@example.com"
        )
        
        self.user2 = User.objects.create_user(
            username="user",
            password="1Q_az_2wsx_3edc",
            email="user@example.com"
        )
        
        self.company = Company.objects.create(
            name="name", 
            description="description", 
            owner=self.user
            )
        
        self.company2 = Company.objects.create(
        name="company 2", 
        description="description", 
        owner=self.user
        )
        
        CompanyMember.objects.create(user=self.user, company=self.company, role=CompanyMember.Role.ADMIN)
        CompanyMember.objects.create(user=self.user2, company=self.company, role=CompanyMember.Role.MEMBER)
        
        self.quiz = Quiz.objects.create(
            title="title1",
            description="description",
            frequency_days=1,
            company=self.company
        )
        
        self.quiz2 = Quiz.objects.create(
            title="Quiz 2",
            description="Description for Quiz 2",
            frequency_days=1,
            company=self.company
        )

        self.quiz3 = Quiz.objects.create(
            title="Quiz 3",
            description="Description for Quiz 3",
            frequency_days=1,
            company=self.company2
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
        
        self.question3 = Question.objects.create(
            quiz=self.quiz,
            text="2 + 2?",
            answers=["4", "3", "5"],
            correct_answer=["4"]
        )

        self.quiz_passing = UserQuizSession.objects.create(
            user=self.user2,
            quiz=self.quiz,
            status=UserQuizSession.Status.STARTED,
            start_session_time=timezone.now()
        )
        
        self.user_quiz1_result = QuizResult.objects.create(
            user=self.user,
            quiz=self.quiz,
            correct_answers=8,
            total_questions=10,
            quiz_time=timedelta(minutes=15)
        )

        self.user_quiz2_result = QuizResult.objects.create(
            user=self.user,
            quiz=self.quiz2,
            correct_answers=7,
            total_questions=10,
            quiz_time=timedelta(minutes=15)
        )

        self.user_quiz3_result = QuizResult.objects.create(
            user=self.user,
            quiz=self.quiz3,
            correct_answers=5,
            total_questions=10,
            quiz_time=timedelta(minutes=15)
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
        
    def test_start_quiz_success(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(f'/api/v1/quizzes/start-quiz/?quiz={self.quiz.id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        quiz_passing_exists = UserQuizSession.objects.filter(user=self.user, quiz=self.quiz).exists()
        self.assertEqual(quiz_passing_exists, True)
        response_data = response.json()
        self.assertIn('session_id', response_data)
        self.assertIn('start_session_time', response_data)
        quiz_data = response_data['questions']
        for question in quiz_data:
            self.assertEqual(question['correct_answer'], [])
            
    def test_complete_quiz_success(self):
        user_answers = [
            {"id": self.question1.id, "correct_answer": ["answers4", "answers6"]},
            {"id": self.question2.id, "correct_answer": ["answers1"]},
            {"id": self.question3.id, "correct_answer": ["5"]}
        ]
        self.client.force_authenticate(user=self.user2)
        response = self.client.post(
            '/api/v1/quizzes/finish-quiz/', 
            {'session': self.quiz_passing.id, 'answers': user_answers},
            format='json'
        )
 
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        quiz_result = QuizResult.objects.last()
        self.assertIsNotNone(quiz_result)
        self.assertEqual(quiz_result.correct_answers, 2)
        self.assertEqual(quiz_result.total_questions, 3)
        self.assertIsInstance(quiz_result.quiz_time, timezone.timedelta)
        self.quiz_passing.refresh_from_db()
        self.assertEqual(self.quiz_passing.status, UserQuizSession.Status.COMPLETED)

    def test_user_company_score(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(f'/api/v1/quizzes/user-company-score/?company_id={self.company.id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        total_correct = self.user_quiz1_result.correct_answers + self.user_quiz2_result.correct_answers
        total_questions = self.user_quiz1_result.total_questions + self.user_quiz2_result.total_questions
        expected_average_score = (total_correct / total_questions) * 100
        self.assertEqual(response.data['company_average_score'], round(expected_average_score, 2))

    def test_user_score(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(f'/api/v1/quizzes/user-rating/?user_id={self.user.id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        total_correct = (self.user_quiz1_result.correct_answers + 
                         self.user_quiz2_result.correct_answers +
                         self.user_quiz3_result.correct_answers)
        total_questions = (self.user_quiz1_result.total_questions + 
                           self.user_quiz2_result.total_questions +
                           self.user_quiz3_result.total_questions)
        expected_average_score = (total_correct / total_questions) * 100
        self.assertEqual(response.data['user_rating'], round(expected_average_score, 2))


class AnaliticTestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="admin",
            password="1Q_az_2wsx_3edc",
            email="owner@example.com"
        )
        
        self.user2 = User.objects.create_user(
            username="user",
            password="1Q_az_2wsx_3edc",
            email="user@example.com"
        )
        
        self.company = Company.objects.create(
            name="Company 1", 
            description="description",
            owner=self.user
        )
        
        self.company2 = Company.objects.create(
            name="Company 2", 
            description="description", 
            owner=self.user
        )

        CompanyMember.objects.create(user=self.user, company=self.company, role=CompanyMember.Role.ADMIN)
        CompanyMember.objects.create(user=self.user2, company=self.company, role=CompanyMember.Role.MEMBER)
        
        self.quiz1 = Quiz.objects.create(
            title="Quiz 1",
            description="description",
            frequency_days=1,
            company=self.company
        )
        
        self.quiz2 = Quiz.objects.create(
            title="Quiz 2",
            description="description",
            frequency_days=1,
            company=self.company2
        )

        self.user_quiz_result1 = QuizResult.objects.create(
            user=self.user,
            quiz=self.quiz1,
            correct_answers=8,
            total_questions=10,
            quiz_time=timedelta(minutes=15)
        )

        self.user_quiz_result2 = QuizResult.objects.create(
            user=self.user,
            quiz=self.quiz2,
            correct_answers=7,
            total_questions=10,
            quiz_time=timedelta(minutes=15)
        )

        self.user_quiz_result3 = QuizResult.objects.create(
            user=self.user2,
            quiz=self.quiz1,
            correct_answers=9,
            total_questions=10,
            quiz_time=timedelta(minutes=20)
        )

        self.user_quiz_result4 = QuizResult.objects.create(
            user=self.user2,
            quiz=self.quiz2,
            correct_answers=6,
            total_questions=10,
            quiz_time=timedelta(minutes=10)
        )

        self.user_quiz_result5 = QuizResult.objects.create(
            user=self.user,
            quiz=self.quiz1,
            correct_answers=6,
            total_questions=10,
            quiz_time=timedelta(minutes=20)
        )

        self.user_quiz_result6 = QuizResult.objects.create(
            user=self.user2,
            quiz=self.quiz2,
            correct_answers=8,
            total_questions=10,
            quiz_time=timedelta(minutes=18)
        )
