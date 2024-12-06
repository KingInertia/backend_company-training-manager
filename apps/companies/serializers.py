from django.utils.translation import gettext as _
from rest_framework import serializers

from .models import Company, CompanyInvitation, CompanyMember, CompanyRequest


class CompanySerializer(serializers.ModelSerializer):
    owner = serializers.PrimaryKeyRelatedField(read_only=True)
    owner_name = serializers.CharField(source='owner.username', read_only=True)
    class Meta:
        model = Company
        fields = ['id', 'name', 'description', 'created_at', 'visibility', 'owner', 'owner_name'] 


class CompanyListSerializer (serializers.ModelSerializer):
    owner_name = serializers.CharField(source='owner.username', read_only=True)
    class Meta:
        model = Company
        fields = ['id', 'name',  'created_at', 'description', 'visibility', 'owner', 'owner_name']
        
        
class CompanyNamesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ['id', 'name']


class CompanyInvitationSerializer(serializers.ModelSerializer):
    sender = serializers.PrimaryKeyRelatedField(read_only=True)
    sender_name = serializers.CharField(source='sender.username', read_only=True)
    receiver_name = serializers.CharField(source='receiver.username', read_only=True)
    company_name = serializers.CharField(source='company.name', read_only=True)
    
    class Meta:
        model = CompanyInvitation
        fields = ['id', 'sender', 'receiver', 'sender_name', 'receiver_name',
                  'company_name','created_at', 'company', 'status']
        
    def create(self, validated_data):
        sender = self.context['request'].user
        receiver = validated_data.get('receiver')
        company = validated_data.get('company')

        if company.owner != sender:
            raise serializers.ValidationError(_("You must be the owner of the company to send an invitation."))
        
        if CompanyMember.objects.filter(user=receiver, company=company).exists():
            raise serializers.ValidationError(_("User is already a member of this company."))
        
        existing_invitation = CompanyInvitation.objects.filter(
            receiver=receiver,
            company=company,
            status = CompanyInvitation.InvitationState.PENDING
            ).exists()

        if existing_invitation :
            raise serializers.ValidationError(_("Invitation already processed."))

        invitation = CompanyInvitation.objects.create(
            sender=sender,
            receiver=receiver,
            company=company,
            status=CompanyRequest.RequestState.PENDING
        )

        return invitation
    
    def update(self, instance, validated_data):
        raise serializers.ValidationError(_("Direct update of invitations is not allowed."))
    
    
class CompanyRequestSerializer(serializers.ModelSerializer):
    sender = serializers.PrimaryKeyRelatedField(read_only=True)
    receiver = serializers.PrimaryKeyRelatedField(read_only=True)
    sender_name = serializers.CharField(source='sender.username', read_only=True)
    receiver_name = serializers.CharField(source='receiver.username', read_only=True)
    company_name = serializers.CharField(source='company.name', read_only=True)

    class Meta:
        model = CompanyRequest
        fields = ['id', 'sender', 'receiver', 'sender_name', 'receiver_name',
                  'company_name','created_at', 'company', 'status']

    def create(self, validated_data):
        sender = self.context['request'].user
        company = validated_data.get('company')
      
        if CompanyMember.objects.filter(user=sender, company=company).exists():
            raise serializers.ValidationError(_("User is already a member of this company."))
        
        existing_request = CompanyRequest.objects.filter(
            sender=sender, company=company, status=CompanyRequest.RequestState.PENDING).exists()

        if existing_request:
            raise serializers.ValidationError(_("Request already processed."))
    
        request = CompanyRequest.objects.create(
            sender=sender,receiver=company.owner,
            company=company,
            status=CompanyRequest.RequestState.PENDING)

        return request

    def update(self, instance, validated_data):
        raise serializers.ValidationError(_("Direct update of requests is not allowed."))


class CompanyMemberSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = CompanyMember
        fields = ['id', 'user_name', 'company', 'user', 'role']
        
    def create(self, validated_data):
        raise serializers.ValidationError(_("Direct creation of company members is not allowed."))
    
    def update(self, instance, validated_data):
        raise serializers.ValidationError(_("Direct update of company members is not allowed."))