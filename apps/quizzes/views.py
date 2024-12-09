from django.db.models import Q
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.companies.models import Company, CompanyMember

from .models import Quiz, QuizResult, UserQuizPassing
from .serializers import QuizForUserSerializer, QuizResultSerializer, QuizSerializer


class QuizViewSet(viewsets.ModelViewSet):
    queryset = Quiz.objects.all()
    serializer_class = QuizSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        company_ids = Company.objects.filter(memberships__user=user).values_list('id', flat=True)
        quizzes = Quiz.objects.filter(company__id__in=company_ids).prefetch_related('questions')
        
        return quizzes   

    def perform_destroy(self, instance):
        user = self.request.user
        company = instance.company

        is_admin_owner = CompanyMember.objects.filter(
            Q(role=CompanyMember.Role.OWNER) | 
            Q(role=CompanyMember.Role.ADMIN), 
            user=user, company=company
        ).exists()

        if not is_admin_owner:
            raise PermissionDenied("User is not Admin or Owner of the company.")

        instance.delete()

    @action(detail=False, methods=['get'], url_path='company-quizzes')
    def company_quizzes_list(self, request):
        company_id = request.query_params.get('company')
        user = self.request.user
        
        if not company_id:
            return Response({"detail": "Company ID is required."}, status=status.HTTP_400_BAD_REQUEST)
        
        role = CompanyMember.objects.filter(user=user, company_id=company_id).values_list('role', flat=True).first()

        if not role:
            return Response({"detail": "User is not a member of this company."}, status=status.HTTP_404_NOT_FOUND)

        if role == CompanyMember.Role.OWNER or role == CompanyMember.Role.ADMIN:
            quizzes = Quiz.objects.filter(company__id=company_id).prefetch_related('questions')
            serializer = QuizSerializer(quizzes, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            quizzes = Quiz.objects.filter(company__id=company_id).only(
                'id', 'title', 'description', 'created_at', 'frequency_days', 'company'
                )
            serializer = QuizForUserSerializer(quizzes, many=True, context={'request': request, 'role': role})
            return Response(serializer.data, status=status.HTTP_200_OK)
        
    @action(detail=False, methods=['get'], url_path='start-quiz')
    def start_quiz(self, request):
        quiz_id = request.query_params.get('quiz')
        user = self.request.user
        
        if not quiz_id:
            return Response({"detail": "Quize ID is required."}, status=status.HTTP_400_BAD_REQUEST)
        
        if not Quiz.objects.filter(id=quiz_id).exists():
            return Response({"detail": "Quiz not found."}, status=status.HTTP_404_NOT_FOUND)
        
        quiz = Quiz.objects.prefetch_related('questions').get(id=quiz_id)
        
        company_id = quiz.company.id
        
        membership = CompanyMember.objects.filter(user=user, company_id=company_id).exists()
        
        if not membership:
            return Response({"detail": "User is not a member of this company."},
                            status=status.HTTP_404_NOT_FOUND)
        
        quiz_passing = UserQuizPassing.objects.filter(user=user, quiz=quiz,
            status=UserQuizPassing.Status.STARTED).only('id', 'start_test_time').first()

        if not quiz_passing:
            quiz_passing = UserQuizPassing.objects.create(user=user, quiz=quiz)
        
        for question in quiz.questions.all():
            question.correct_answer = []

        quiz_data = QuizSerializer(quiz).data

        response_data = {
            'start_test_time': quiz_passing.start_test_time,
            'test_id': quiz_passing.id,
            'quiz': quiz_data,
        }

        return Response(response_data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='finish-quiz')
    def finish_quiz(self, request):
        quiz_passing_id = request.data.get('quiz_passing_id')
        user_answers = request.data.get('questions', [])
        user = request.user
        end_time = timezone.now()

        if not quiz_passing_id or not user_answers:
            return Response({"detail": "Quiz passing ID and questions are required."},
                            status=status.HTTP_400_BAD_REQUEST)

        if not UserQuizPassing.objects.filter(id=quiz_passing_id, user=user).exists():
            return Response({"detail": "Quiz passing not found."}, status=status.HTTP_404_NOT_FOUND)
        
        quiz_passing = UserQuizPassing.objects.get(id=quiz_passing_id)

        if quiz_passing.status == UserQuizPassing.Status.COMPLETED:
            return Response({"detail": "Quiz already completed."}, status=status.HTTP_400_BAD_REQUEST)

        quiz_passing.status = UserQuizPassing.Status.COMPLETED
        quiz_passing.end_test_time = end_time
        quiz_passing.save()
        
        correct_answers = quiz_passing.quiz.questions.values('id', 'correct_answer')
        correct_count = 0    
        
        for user_answer in user_answers:
            for correct_answer in correct_answers:
                if user_answer['id'] == correct_answer['id']:
                    if sorted(user_answer['correct_answer']) == sorted(correct_answer['correct_answer']):
                        correct_count += 1
                    break

        quiz_result = QuizResult.objects.create(
            user=user,
            quiz=quiz_passing.quiz,
            correct_answers=correct_count,
            total_questions=len(correct_answers),
            test_time=quiz_passing.end_test_time - quiz_passing.start_test_time
        )

        serializer = QuizResultSerializer(quiz_result)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['get'], url_path='user-company-score')
    def user_company_average_score(self, request):
        user = request.user
        company_id = request.query_params.get('company_id')

        if not company_id:
            return Response({"detail": "Company ID is required."}, status=status.HTTP_400_BAD_REQUEST)

        if not Company.objects.filter(id=company_id).exists():
            return Response({"detail": "Company not found."}, status=status.HTTP_404_NOT_FOUND)

        company_quiz_results = QuizResult.objects.filter(
            user=user,
            quiz__company_id=company_id
        ).values('correct_answers', 'total_questions')
        correct_questions_count= sum(result['correct_answers'] for result in company_quiz_results)
        questions_count = sum(result['total_questions'] for result in company_quiz_results)

        if questions_count:
            average_score = (correct_questions_count / questions_count) * 100
        else:
            average_score = 0

        return Response({
            'company_average_score': round(average_score, 2)
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='user-score')
    def user_average_score(self, request):
        user = request.user

        company_quiz_results = QuizResult.objects.filter(
            user=user,
        ).values('correct_answers', 'total_questions')
        correct_questions_count= sum(result['correct_answers'] for result in company_quiz_results)
        questions_count = sum(result['total_questions'] for result in company_quiz_results)

        if questions_count:
            average_score = (correct_questions_count / questions_count) * 100
        else:
            average_score = 0

        return Response({
            'user_average_score': round(average_score, 2)
        }, status=status.HTTP_200_OK)