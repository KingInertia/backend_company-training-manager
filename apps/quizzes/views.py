from django.db.models import Q
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.companies.models import Company, CompanyMember

from .models import Quiz, QuizResult, UserQuizSession
from .permissions import IsCompanyAdminOrOwner
from .resources import QuizResultResource
from .serializers import QuizForUserSerializer, QuizResultSerializer, QuizSerializer, QuizStartSessionSerializer


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
                'id', 'title', 'description', 'created_at', 'frequency_days'
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
        
        quiz = Quiz.objects.select_related('company').prefetch_related('questions').get(id=quiz_id)
        
        company_id = quiz.company.id
        
        membership = CompanyMember.objects.filter(user=user, company_id=company_id).exists()

        if not membership:
            return Response({"detail": "User is not a member of this company."},
                            status=status.HTTP_404_NOT_FOUND)

        quiz_session = UserQuizSession.objects.filter(user=user, quiz=quiz,
            status=UserQuizSession.Status.STARTED).only('id', 'start_session_time').first()

        if not quiz_session:
            quiz_session = UserQuizSession.objects.create(user=user, quiz=quiz)
        
        for question in quiz.questions.all():
            question.correct_answer = []

        response_data = QuizStartSessionSerializer({
            'start_session_time': quiz_session.start_session_time,
            'session_id': quiz_session.id,
            'questions': quiz.questions.all()
        }).data    
        
        return Response(response_data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='finish-quiz')
    def finish_quiz(self, request):
        quiz_session_id = request.data.get('session')
        user_answers = request.data.get('answers', [])
        user = request.user
        end_time = timezone.now()

        if not quiz_session_id or not user_answers:
            return Response({"detail": "Quiz session_id ID and answers are required."},
                            status=status.HTTP_400_BAD_REQUEST)

        if not UserQuizSession.objects.filter(id=quiz_session_id, user=user).exists():
            return Response({"detail": "Quiz session_id not found."}, status=status.HTTP_404_NOT_FOUND)
        
        quiz_session = UserQuizSession.objects.prefetch_related('quiz__questions').get(id=quiz_session_id)

        if quiz_session.status == UserQuizSession.Status.COMPLETED:
            return Response({"detail": "Quiz already completed."}, status=status.HTTP_400_BAD_REQUEST)

        quiz_session.status = UserQuizSession.Status.COMPLETED
        quiz_session.end_session_time = end_time
        quiz_session.save()
        
        questions = quiz_session.quiz.questions.all()
            
        correct_count = 0    
        for user_answer in user_answers:
            for question in questions:
                if user_answer['id'] == question.id:
                    if sorted(user_answer['correct_answer']) == sorted(question.correct_answer):
                        correct_count += 1
                    break

        quiz_result = QuizResult.objects.create(
            user=user,
            quiz=quiz_session.quiz,
            correct_answers=correct_count,
            total_questions=len(questions),
            quiz_time=quiz_session.end_session_time - quiz_session.start_session_time
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
        
    @action(detail=False, methods=['get'], url_path='quiz-info')
    def quiz_info(self, request):
        quiz_id = request.query_params.get('quiz')
        user = self.request.user
        
        try:
            quiz = Quiz.objects.filter(id=quiz_id).select_related('company').only(
                'id', 'title', 'description', 'created_at', 'frequency_days', 'company__id'
            ).first()
        except Quiz.DoesNotExist:
            return Response({"detail": "Quiz not found."}, status=status.HTTP_404_NOT_FOUND)
        
        if not CompanyMember.objects.filter(company=quiz.company.id, user=user).exists():
            return Response(
                {"detail": "User is not a member of this company."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = QuizForUserSerializer(quiz, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='export-result-csv')
    def export_result_csv(self, request):
        user = request.user
        quiz_id = request.query_params.get('quiz_id')
        
        if quiz_id is None:
            return Response({"error": "quiz_id is required"}, status=400)
        
        try:
            quiz_result = QuizResult.objects.filter(quiz__id =quiz_id, user=user).latest('created_at')
        except QuizResult.DoesNotExist:
            return Response({"detail": "Result not found."}, status=status.HTTP_404_NOT_FOUND)
        
        result_data = QuizResultResource().export([quiz_result])
        response = HttpResponse(result_data.csv)
        response['Content-Disposition'] = 'attachment; filename="results.csv"'

        return response
    
    @action(detail=False, methods=['get'], url_path='export-result-json')
    def export_result_json(self, request):
        user = request.user
        quiz_id = request.query_params.get('quiz_id')
        
        if quiz_id is None:
            return Response({"error": "quiz_id is required"}, status=400)
        
        try:
            quiz_result = QuizResult.objects.filter(quiz__id=quiz_id, user=user).latest('created_at')      
        except QuizResult.DoesNotExist:
            return Response({"detail": "Result not found."}, status=status.HTTP_404_NOT_FOUND)
        
        result_data = QuizResultResource().export([quiz_result])
        
        data = [result_data.dict]
        
        response = HttpResponse(data, content_type='application/json')
        response['Content-Disposition'] = 'attachment; filename="results.json"'

        return response


    @action(detail=False, methods=['get'], url_path='company-results-csv', permission_classes=[ IsCompanyAdminOrOwner])
    def export_company_results_csv(self, request):
        company_id = request.query_params.get('company_id')

        try:
            quiz_results = QuizResult.objects.filter( quiz__company_id=company_id)
        except QuizResult.DoesNotExist:
            return Response({"detail": "Results not found."}, status=404)
        
        result_data = QuizResultResource().export(quiz_results)
        response = HttpResponse(result_data.csv, content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="company_results.csv"'

        return response

    @action(detail=False, methods=['get'], url_path='company-results-json', permission_classes=[ IsCompanyAdminOrOwner])
    def export_company_results_json(self, request):
        company_id = request.query_params.get('company_id')

        try:
            quiz_results = QuizResult.objects.filter( quiz__company_id=company_id)
        except QuizResult.DoesNotExist:
            return Response({"detail": "Results not found."}, status=404)
        
        result_data = QuizResultResource().export(quiz_results)
        data = [result_data.dict]
        
        response = HttpResponse(data, content_type='application/json')
        response['Content-Disposition'] = 'attachment; filename="company_results.json"'

        return response

    @action(detail=False, methods=['get'], url_path='user-results-csv', permission_classes=[ IsCompanyAdminOrOwner])
    def export_user_results_csv(self, request):
        company_id = request.query_params.get('company_id')
        user_id = request.query_params.get('user_id')

        try:
            quiz_results = QuizResult.objects.filter( quiz__company_id=company_id, user_id=user_id)
        except QuizResult.DoesNotExist:
            return Response({"detail": "Result not found."}, status=404)
        
        result_data = QuizResultResource().export(quiz_results)

        response = HttpResponse(result_data.csv, content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="user_results.csv"'

        return response
    
    @action(detail=False, methods=['get'], url_path='user-results-json', permission_classes=[ IsCompanyAdminOrOwner])
    def export_user_results_json(self, request):
        company_id = request.query_params.get('company_id')
        user_id = request.query_params.get('user_id')

        try:
            quiz_results = QuizResult.objects.filter( quiz__company_id=company_id, user_id=user_id)
        except QuizResult.DoesNotExist:
            return Response({"detail": "Result not found."}, status=404)
        
        result_data = QuizResultResource().export(quiz_results)
        data = [result_data.dict]
        response = HttpResponse(data, content_type='application/json')
        response['Content-Disposition'] = 'attachment; filename="user_results.json"'

        return response
