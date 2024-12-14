from django.db.models import Q
from rest_framework import serializers

from apps.companies.models import CompanyMember

from .models import Question, Quiz, QuizResult, UserQuizSession


class QuestionSerializer(serializers.ModelSerializer):
    quiz = serializers.PrimaryKeyRelatedField(queryset=Quiz.objects.all(), required=False) 
    
    class Meta:
        model = Question
        fields = ['id', 'text', 'answers', 'correct_answer', 'quiz']
        extra_kwargs = {
            'id': {'read_only': False, 'required': False},
        }


class QuizSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True)

    class Meta:
        model = Quiz
        fields = ['id', 'title', 'description', 'created_at', 'frequency_days', 'questions', 'company']
        
    def create(self, validated_data):
        user = self.context['request'].user
        company = validated_data.get('company') 

        is_admin_owner = CompanyMember.objects.filter(
            Q(role=CompanyMember.Role.OWNER) | 
            Q(role=CompanyMember.Role.ADMIN), 
            user=user, company=company
            ).exists()
        
        if (not is_admin_owner):
            raise serializers.ValidationError(("User is not Admin or Owner of company."))
        
        questions_data = validated_data.pop('questions')
                
        if len(questions_data) < 2: 
            raise serializers.ValidationError("A quiz must have at least two questions.") 
        for question_data in questions_data: 
            if len(question_data['answers']) < 2: 
                raise serializers.ValidationError("Each question must have at least two answer options.") 
            if len(question_data['correct_answer']) == 0: 
                raise serializers.ValidationError("Each question must have at least one correct answer.")
            if not all(answer in question_data['answers'] for answer in question_data['correct_answer']):
                raise serializers.ValidationError("Correct answer must be one of the answer options.")
            
        quiz = Quiz.objects.create(**validated_data)
        questions = []
        for question_data in questions_data:
            question = Question(
                quiz=quiz,
                text=question_data['text'],
                answers=question_data['answers'],
                correct_answer=question_data['correct_answer']
            )
            questions.append(question)

        Question.objects.bulk_create(questions)
    
        return quiz

    def update(self, instance, validated_data):
        user = self.context['request'].user
        company = instance.company

        is_admin_owner = CompanyMember.objects.filter(
            Q(role=CompanyMember.Role.OWNER) | 
            Q(role=CompanyMember.Role.ADMIN), 
            user=user, company=company
        ).exists()

        if not is_admin_owner:
            raise serializers.ValidationError("User is not Admin or Owner of the company.")
        
        new_questions = validated_data.get('questions', [])
        
        if len(new_questions) < 2: 
            raise serializers.ValidationError("A quiz must have at least two questions.") 
        
        for question in new_questions: 
            if len(question['answers']) < 2: 
                raise serializers.ValidationError("Each question must have at least two answer options.") 
            if len(question['correct_answer']) == 0: 
                raise serializers.ValidationError("Each question must have at least one correct answer.")
            if not set(question['correct_answer']).issubset(set(question['answers'])):
                raise serializers.ValidationError("Correct answers must be among the answer options.")

        instance.title = validated_data.get('title', instance.title)
        instance.description = validated_data.get('description', instance.description)
        instance.frequency_days = validated_data.get('frequency_days', instance.frequency_days)
        instance.save()

        current_questions = instance.questions.all()    
        
        current_questions_ids = set()
        for question in current_questions:
            current_questions_ids.add(question.id)

        questions_to_create = []
        questions_to_update = []
        new_question_ids = set()

        for new_question in new_questions:
            if 'id' in new_question:
                new_question_ids.add(new_question['id'])
                question_id = new_question['id']
                if question_id in current_questions_ids:
                    old_question = current_questions.get(id=question_id)
                    old_question.text = new_question['text']
                    old_question.answers = new_question['answers']
                    old_question.correct_answer = new_question['correct_answer']
                    questions_to_update.append(old_question)
                    
            else:
                new_question['quiz'] = instance
                questions_to_create.append(Question(**new_question))
            
        if new_question_ids:
            instance.questions.filter(~Q(id__in=new_question_ids)).delete()
            
        if questions_to_create:
            Question.objects.bulk_create(questions_to_create)
            
        if questions_to_update:
            Question.objects.bulk_update(questions_to_update, ['text', 'answers', 'correct_answer'])
        
        return instance


class QuizForUserSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Quiz
        fields = ['id', 'title', 'description', 'created_at', 'frequency_days']
        

class UserQuizSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserQuizSession
        fields = ['id', 'user', 'quiz', 'status', 'start_session_time']
        

class QuizStartSessionSerializer(serializers.Serializer):
    start_session_time = serializers.DateTimeField()
    session_id = serializers.IntegerField()
    questions = QuestionSerializer(many=True)


class QuizResultSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = QuizResult
        fields = ['id', 'user', 'quiz', 'correct_answers', 'total_questions', 'quiz_time']
        
        
class QuizLastCompletionSerializers(serializers.ModelSerializer):
    quiz_title = serializers.CharField(source='quiz.title', read_only=True)
    
    class Meta:
        model = QuizResult
        fields = ['id', 'quiz', 'created_at', 'quiz_title']
        

class UserLastCompletionSerializers(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = QuizResult
        fields = ['id', 'user', 'created_at', 'user_name']
        

class DynamicTimeSerializer(serializers.Serializer):
    day = serializers.DateTimeField()
    average_score = serializers.FloatField()


class DynamicScoreSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    dynamic_time = DynamicTimeSerializer(many=True)