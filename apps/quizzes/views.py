from django.db.models import Q, Sum
from django.db.models.functions import TruncDay
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.timezone import make_aware
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.companies.models import Company, CompanyMember

from .models import Quiz, QuizResult, UserQuizSession
from .permissions import IsCompanyAdminOrOwner
from .serializers import (
    DynamicScoreSerializer,
    QuizForUserSerializer,
    QuizLastCompletionSerializers,
    QuizResultSerializer,
    QuizSerializer,
    QuizStartSessionSerializer,
    UserLastCompletionSerializers,
)
from .utils import FileType, FilterType, create_analitycs_data, export_quiz_results


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
        correct_questions_count = sum(result['correct_answers'] for result in company_quiz_results)
        questions_count = sum(result['total_questions'] for result in company_quiz_results)

        if questions_count:
            average_score = (correct_questions_count / questions_count) * 100
        else:
            average_score = 0

        return Response({
            'company_average_score': round(average_score, 2)
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='user-rating')
    def user_rating(self, request):
        user_id = request.query_params.get('user_id')

        company_quiz_results = QuizResult.objects.filter(
            user=user_id,
        ).values('correct_answers', 'total_questions')
        correct_questions_count = sum(result['correct_answers'] for result in company_quiz_results)
        questions_count = sum(result['total_questions'] for result in company_quiz_results)

        if questions_count:
            average_score = (correct_questions_count / questions_count) * 100
        else:
            average_score = 0
        return Response({
            'user_rating': round(average_score, 2)
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

    @action(detail=False, methods=['get'], url_path='export-result')
    def export_result(self, request):
        user = request.user
        quiz_id = request.query_params.get('quiz_id')
        file_type = request.query_params.get('file_type')
        
        if quiz_id is None:
            return Response({"error": "quiz_id is required"}, status=400)
        
        try:
            file_type = FileType(file_type)
        except ValueError:
            return Response({"error": "Unsupported type."}, status=400)
        
        quiz_result = QuizResult.objects.filter(quiz__id=quiz_id, user=user).latest('created_at')
        
        if not quiz_result:
            return Response({"detail": "Result not found."}, status=404)
        
        return export_quiz_results([quiz_result], file_type)

    @action(
        detail=False, methods=['get'],
        url_path='export-company-results',
        permission_classes=[IsCompanyAdminOrOwner]
        )
    def export_company_results(self, request):
        company_id = request.query_params.get('company_id')
        user_id = request.query_params.get('user_id')
        file_type = request.query_params.get('file_type', 'json')

        if not company_id:
            return Response({"error": "company_id is required"}, status=400)

        try:
            file_type = FileType(file_type)
        except ValueError:
            return Response({"error": "Unsupported type."}, status=400)

        if user_id:
            quiz_results = QuizResult.objects.filter(quiz__company_id=company_id, user_id=user_id)
        else:
            quiz_results = QuizResult.objects.filter(quiz__company_id=company_id)
            
        if not quiz_results:
            return Response({"detail": "Result not found."}, status=404)

        return export_quiz_results(quiz_results, file_type)

    @action(detail=False, methods=['get'], url_path='quiz-last-completions', permission_classes=[IsCompanyAdminOrOwner])
    def quizzes_last_completions(self, request):
        company_id = request.query_params.get('company_id')

        if not company_id:
            return Response({'error': 'company_id is required'}, status=400)
        
        if not Company.objects.filter(id=company_id).exists():
            return Response({"detail": "Company not found."}, status=status.HTTP_404_NOT_FOUND)
        
        quizzes = Quiz.objects.filter(company_id=company_id).values_list('id', flat=True)

        quizzes_results = QuizResult.objects.filter(
            quiz__in=quizzes
            ).order_by('quiz', '-created_at').distinct('quiz')

        serializer = QuizLastCompletionSerializers(quizzes_results, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'], url_path='dynamic-scores')
    def dynamic_time_scores(self, request):
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        filter_by = request.query_params.get('type')
        
        if not start_date or not end_date:
            return Response({'error': 'start_date and end_date are required'}, status=400)
        
        if not filter_by:
            return Response({'error': 'filter_type are required quiz or user'}, status=400)
        
        if filter_by:
            try:
                filter_by = FilterType(filter_by).value
            except ValueError:
                return Response({"error": "Unsupported filter type."}, status=400)
        try:
            start_date = make_aware(parse_datetime(start_date))
            end_date = make_aware(parse_datetime(end_date))
        except ValueError:
            return Response({'error': 'Invalid date format.'}, status=400)
  
        dynamic_scores = QuizResult.objects.filter(
        created_at__range=[start_date, end_date]
        ).annotate(
        day=TruncDay('created_at')
        ).values(filter_by, 'day').annotate(
        total_correct_answers=Sum('correct_answers'),
        total_total_questions=Sum('total_questions')
        ).order_by(filter_by, 'day')

        if not dynamic_scores:
            return Response({"error": "No data found for the given date range."}, status=404)
        
        serializer = DynamicScoreSerializer(create_analitycs_data(dynamic_scores, FilterType(filter_by)), many=True)
        
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='user-dynamic-scores')
    def user_dynamic_scores(self, request):
        user = request.user
        start_date = user.created_at
        end_date = timezone.now()
        
        filter_by = FilterType.QUIZ.value
        dynamic_scores = QuizResult.objects.filter(
        created_at__range=[start_date, end_date], user=user, 
        ).annotate(
        day=TruncDay('created_at')
        ).values(filter_by, 'day').annotate(
        total_correct_answers=Sum('correct_answers'),
        total_total_questions=Sum('total_questions')
        ).order_by(filter_by, 'day')

        if not dynamic_scores:
            return Response({"error": "No data found for the given date range."}, status=404)
        
        serializer = DynamicScoreSerializer(create_analitycs_data(dynamic_scores, FilterType(filter_by)), many=True)
        
        return Response(serializer.data)
    
    @action(
        detail=False, methods=['get'],
        url_path='users-last-completions',
        permission_classes=[IsCompanyAdminOrOwner])
    def users_last_completions(self, request):
        company_id = request.query_params.get('company_id')

        if not company_id:
            return Response({'error': 'company_id is required'}, status=400)
        
        if not Company.objects.filter(id=company_id).exists():
            return Response({"detail": "Company not found."}, status=status.HTTP_404_NOT_FOUND)

        users_id = CompanyMember.objects.filter(company_id=company_id).values_list('user', flat=True)
        users_results = (
            QuizResult.objects.filter(user__in=users_id, quiz__company=company_id)
            .order_by('user', '-created_at')
            .distinct('user')
        )
        serializer = UserLastCompletionSerializers(users_results, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(
        detail=False,
        methods=['get'],
        url_path='company-dynamic-scores',
        permission_classes=[IsCompanyAdminOrOwner])
    def company_time_scores(self, request):
        user_id = request.query_params.get('user_id')
        company_id = request.query_params.get('company_id')

        if not company_id:
            return Response({'error': 'company_id is required'}, status=400)
        
        create_date = Company.objects.filter(id=company_id).values('created_at').first()
        if not create_date:
            return Response({"detail": "Company not found."}, status=status.HTTP_404_NOT_FOUND)
        start_date = create_date['created_at']
        end_date = timezone.now()

        if (user_id):
            filter_by = FilterType.QUIZ.value
            dynamic_scores = QuizResult.objects.filter(
            created_at__range=[start_date, end_date], user=user_id, quiz__company=company_id
            ).annotate(
            day=TruncDay('created_at')
            ).values(filter_by, 'day').annotate(
            total_correct_answers=Sum('correct_answers'),
            total_total_questions=Sum('total_questions')
            ).order_by(filter_by, 'day')
        else:
            filter_by = FilterType.USER.value
            dynamic_scores = QuizResult.objects.filter(
            created_at__range=[start_date, end_date], quiz__company=company_id
            ).annotate(
            day=TruncDay('created_at')
            ).values(filter_by, 'day').annotate(
            total_correct_answers=Sum('correct_answers'),
            total_total_questions=Sum('total_questions')
            ).order_by(filter_by, 'day')

        if not dynamic_scores:
            return Response({"error": "No data found for the given date range."}, status=404)
        
        serializer = DynamicScoreSerializer(create_analitycs_data(dynamic_scores, FilterType(filter_by)), many=True)
        
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='user-last-completions')
    def user_last_completions(self, request):
        user = request.user

        users_results = (
            QuizResult.objects.filter(user=user)
            .order_by('quiz', '-created_at')
            .distinct('quiz')
        )
        serializer = QuizLastCompletionSerializers(users_results, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)    