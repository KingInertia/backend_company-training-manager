from django.utils.translation import gettext as _
from rest_framework import serializers

from .enums import RequestState
from .models import Company, CompanyInvitation, CompanyMember, CompanyRequest


class CompanySerializer(serializers.ModelSerializer):
    owner = serializers.PrimaryKeyRelatedField(read_only=True)
    owner_name = serializers.CharField(source='owner.username', read_only=True)
    class Meta:
        model = Company
        fields = ['id', 'name', 'description', 'visibility', 'owner', 'owner_name'] 


class CompanyListSerializer (serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ('__all__')


class CompanyInvitationSerializer(serializers.ModelSerializer):
    sender = serializers.PrimaryKeyRelatedField(read_only=True)
    class Meta:
        model = CompanyInvitation
        fields = '__all__'
        
    def create(self, validated_data):
        sender = self.context['request'].user
        receiver = validated_data.get('receiver')
        company = validated_data.get('company')

        if company.owner != sender:
            raise serializers.ValidationError(_("You must be the owner of the company to send an invitation."))
        
        existing_invitation = CompanyInvitation.objects.filter(
            sender=sender,
            company=company
            ).first()

        if CompanyMember.objects.filter(user=receiver, company=company).exists():
            raise serializers.ValidationError(_("User is already a member of this company."))

        if existing_invitation and existing_invitation.status == RequestState.PENDING:
            raise serializers.ValidationError(_("Invitation already processed."))

        invitation = CompanyInvitation.objects.create(
            sender=sender,
            receiver=receiver,
            company=company,
            status=RequestState.PENDING
        )

        return invitation
    
    def update(self, instance, validated_data):
        raise serializers.ValidationError(_("Direct update of invitations is not allowed."))
    
    
class CompanyRequestSerializer(serializers.ModelSerializer):
    sender = serializers.PrimaryKeyRelatedField(read_only=True)
    receiver = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = CompanyRequest
        fields = '__all__'

    def create(self, validated_data):
        sender = self.context['request'].user
        company = validated_data.get('company')
      
        existing_request = CompanyRequest.objects.filter(sender=sender, company=company).first()
              
        if CompanyMember.objects.filter(user=sender, company=company).exists():
            raise serializers.ValidationError(_("User is already a member of this company."))

        if existing_request and existing_request.status == RequestState.PENDING:
            raise serializers.ValidationError(_("Request already processed."))
    
        request = CompanyRequest.objects.create(
            sender=sender,receiver=company.owner,
            company=company,
            status=RequestState.PENDING)

        return request

    def update(self, instance, validated_data):
        raise serializers.ValidationError(_("Direct update of requests is not allowed."))


class CompanyMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyMember
        fields = '__all__'
        
    def create(self, validated_data):
        raise serializers.ValidationError(_("Direct creation of company members is not allowed."))
    
    def update(self, instance, validated_data):
        raise serializers.ValidationError(_("Direct update of company members is not allowed."))