from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.companies.models import Company, CompanyInvitation, CompanyMember, CompanyRequest

User = get_user_model()


class CompanyInvitationViewSetTests(APITestCase):
    
    def setUp(self):
        self.owner = User.objects.create_user(
            username="owner", 
            password="1Qaz_2wsx_3edc", 
            email="owner@example.com"
        )
        self.receiver1 = User.objects.create_user(
            username="receiver1", 
            password="1Qaz_2wsx_3edc", 
            email="receiver1@example.com"
        )
        
        self.receiver2 = User.objects.create_user(
            username="receiver2", 
            password="1Qaz_2wsx_3edc", 
            email="receiver1@example.com"
        )
        
        self.company1 = Company.objects.create(
            name="Test1", 
            description="Test description", 
            owner=self.owner, 
            visibility=Company.Visibility.VISIBLE  
        )
        
        self.invitation1 = CompanyInvitation.objects.create(
            company=self.company1,
            sender=self.owner,
            receiver=self.receiver1,
            status=CompanyInvitation.InvitationState.PENDING
        )
        self.invitation2 = CompanyInvitation.objects.create(
            company=self.company1,
            sender=self.owner,
            receiver=self.receiver2,
            status=CompanyInvitation.InvitationState.PENDING
        )
        
        self.other_user = User.objects.create_user(
            username="other_user", 
            password="1Qaz_2wsx_3edc", 
            email="other_user@example.com"
        )
        
    def test_accept_invitation_success(self): 
        self.client.force_authenticate(user=self.receiver1)
        url = f'/api/v1/invitations/{self.invitation1.pk}/accept/'
        response = self.client.patch(url)
        assert response.status_code == status.HTTP_200_OK
        self.invitation1.refresh_from_db()
        assert self.invitation1.status == CompanyInvitation.InvitationState.ACCEPTED
        assert CompanyMember.objects.filter(user=self.receiver1, company=self.company1).exists()

    def test_accept_invitation_already_processed(self):
        self.client.force_authenticate(user=self.receiver1)
        self.invitation1.status = CompanyInvitation.InvitationState.ACCEPTED
        self.invitation1.save()
        url = f'/api/v1/invitations/{self.invitation1.pk}/accept/'
        response = self.client.patch(url)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        
    def test_accept_invitation_by_non_receiver(self):
        self.client.force_authenticate(user=self.owner)     
        url = f'/api/v1/invitations/{self.invitation1.pk}/accept/'
        response = self.client.patch(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        self.invitation1.refresh_from_db()
        assert self.invitation1.status == CompanyInvitation.InvitationState.PENDING
        
    def test_accept_invitation_not_found(self):
        self.client.force_authenticate(user=self.receiver1)
        url = '/api/v1/invitations/999/accept/'
        response = self.client.patch(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND
        
    def test_decline_invitation_success(self):
        self.client.force_authenticate(user=self.receiver1)
        url = f'/api/v1/invitations/{self.invitation1.pk}/decline/'
        response = self.client.patch(url)
        assert response.status_code == status.HTTP_200_OK
        self.invitation1.refresh_from_db()
        assert self.invitation1.status == CompanyInvitation.InvitationState.DECLINED

    def test_decline_invitation_already_processed(self):
        self.client.force_authenticate(user=self.receiver1)
        self.invitation1.status = CompanyInvitation.InvitationState.DECLINED
        self.invitation1.save()
        url = f'/api/v1/invitations/{self.invitation1.pk}/decline/'
        response = self.client.patch(url)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        
    def test_decline_invitation_by_non_receiver(self):
        self.client.force_authenticate(user=self.owner)     
        url = f'/api/v1/invitations/{self.invitation1.pk}/decline/'
        response = self.client.patch(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        self.invitation1.refresh_from_db()
        assert self.invitation1.status == CompanyInvitation.InvitationState.PENDING
        
    def test_decline_invitation_not_found(self):
        self.client.force_authenticate(user=self.receiver1)
        url = '/api/v1/invitations/999/decline/'
        response = self.client.patch(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_revoke_invitation_success(self):
        self.client.force_authenticate(user=self.owner)
        url = f'/api/v1/invitations/{self.invitation1.pk}/revoke/'
        response = self.client.patch(url)
        assert response.status_code == status.HTTP_200_OK
        self.invitation1.refresh_from_db()
        assert self.invitation1.status == CompanyInvitation.InvitationState.REVOKED

    def test_revoke_invitation_by_non_owner(self):
        self.client.force_authenticate(user=self.receiver1)        
        url = f'/api/v1/invitations/{self.invitation1.pk}/revoke/'
        response = self.client.patch(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        self.invitation1.refresh_from_db()
        assert self.invitation1.status == CompanyInvitation.InvitationState.PENDING
        
    def test_revoke_invitation_already_processed(self):
        self.client.force_authenticate(user=self.owner)
        self.invitation1.status = CompanyInvitation.InvitationState.ACCEPTED
        self.invitation1.save()
        assert self.invitation1.status == CompanyInvitation.InvitationState.ACCEPTED
        url = f'/api/v1/invitations/{self.invitation1.pk}/revoke/'
        response = self.client.patch(url)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        
    def test_update_invitation_not_allowed(self):
        self.client.force_authenticate(user=self.owner)
        updated_data = {
            "status": CompanyInvitation.InvitationState.ACCEPTED,
        }
        url = f'/api/v1/invitations/{self.invitation1.pk}/'
        response = self.client.patch(url, updated_data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        
    def test_destroy_invitation_permission_denied(self):
        self.client.force_authenticate(user=self.receiver1)
        url = f'/api/v1/invitations/{self.invitation1.pk}/'
        response = self.client.delete(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN    
        
    def test_list_user_invitations(self):
        self.client.force_authenticate(user=self.receiver1)
        url = '/api/v1/invitations/user-invitations/'
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert len(response_data) == 1  
        assert response_data[0]['id'] == self.invitation1.id
        
    def test_list_user_invitations_no_invitations(self):
        self.client.force_authenticate(user=self.other_user)
        url = '/api/v1/invitations/user-invitations/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), [])

    def test_list_owner_invitations(self):
        self.client.force_authenticate(user=self.owner)
        url = '/api/v1/invitations/'
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert len(response_data) == 2
        assert response_data[0]['id'] == self.invitation1.id
        assert response_data[1]['id'] == self.invitation2.id

    def test_list_owner_invitations_no_invitations(self):
        self.client.force_authenticate(user=self.other_user)
        url = '/api/v1/invitations/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), [])

        
class CompanyInvitationSerializerTests(APITestCase):

    def setUp(self):
        self.owner = User.objects.create_user(
            username="owner", 
            password="1Qaz_2wsx_3edc", 
            email="owner@example.com"
        )
        self.receiver1 = User.objects.create_user(
            username="receiver1", 
            password="1Qaz_2wsx_3edc", 
            email="receiver1@example.com"
        )
        self.company1 = Company.objects.create(
            name="Test1", 
            description="Test description", 
            owner=self.owner, 
            visibility=Company.Visibility.VISIBLE  
        )
        
    def test_create_invitation_success(self):
        self.client.force_authenticate(user=self.owner)     
        data = {
            'receiver': self.receiver1.pk,
            'company': self.company1.pk
        }
        url = '/api/v1/invitations/'
        response = self.client.post(url, data)
        assert response.status_code == status.HTTP_201_CREATED
        invitation = CompanyInvitation.objects.last()
        assert invitation.sender == self.owner
        assert invitation.receiver == self.receiver1
        assert invitation.company == self.company1
        assert invitation.status == CompanyInvitation.InvitationState.PENDING

    def test_create_invitation_user_already_member(self):
        CompanyMember.objects.create(user=self.receiver1, company=self.company1)
        self.client.force_authenticate(user=self.owner)
        data = {
            'receiver': self.receiver1.pk,
            'company': self.company1.pk
        }
        url = '/api/v1/invitations/'
        response = self.client.post(url, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        
    def test_create_invitation_already_processed(self):
        self.client.force_authenticate(user=self.owner)
        existing_invitation = CompanyInvitation.objects.create(  # noqa: F841
            sender=self.owner,
            receiver=self.receiver1,
            company=self.company1,
            status=CompanyInvitation.InvitationState.PENDING
        )
        data = {
            'receiver': self.receiver1.pk,
            'company': self.company1.pk
        }
        url = '/api/v1/invitations/'
        response = self.client.post(url, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    
class CompanyRequestViewSetTests(APITestCase):

    def setUp(self):
        self.sender = User.objects.create_user(
            username="sender", 
            password="1Qaz_2wsx_3edc", 
            email="sender@example.com"
        )
        self.receiver = User.objects.create_user(
            username="receiver", 
            password="1Qaz_2wsx_3edc", 
            email="receiver@example.com"
        )
        self.other_user = User.objects.create_user(
            username="other_user", 
            password="1Qaz_2wsx_3edc", 
            email="other_user@example.com"
        )
        self.company = Company.objects.create(
            name="TestCompany", 
            description="Test description", 
            owner=self.receiver, 
            visibility=Company.Visibility.VISIBLE
        )
        self.request = CompanyRequest.objects.create(
            sender=self.sender,
            receiver=self.receiver,
            company=self.company,
            status=CompanyRequest.RequestState.PENDING
        )

    def test_approve_request_success(self):
        self.client.force_authenticate(user=self.receiver)
        url = f'/api/v1/requests/{self.request.pk}/approve/'
        response = self.client.patch(url)
        assert response.status_code == status.HTTP_200_OK
        self.request.refresh_from_db()
        assert self.request.status == CompanyRequest.RequestState.APPROVED
        assert CompanyMember.objects.filter(user=self.sender, company=self.company).exists()

    def test_approve_request_already_processed(self):
        self.client.force_authenticate(user=self.receiver)
        self.request.status = CompanyRequest.RequestState.APPROVED
        self.request.save()
        url = f'/api/v1/requests/{self.request.pk}/approve/'
        response = self.client.patch(url)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_approve_request_by_non_receiver(self):
        self.client.force_authenticate(user=self.sender)
        url = f'/api/v1/requests/{self.request.pk}/approve/'
        response = self.client.patch(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        self.request.refresh_from_db()
        assert self.request.status == CompanyRequest.RequestState.PENDING

    def test_reject_request_success(self):
        self.client.force_authenticate(user=self.receiver)
        url = f'/api/v1/requests/{self.request.pk}/reject/'
        response = self.client.patch(url)
        assert response.status_code == status.HTTP_200_OK
        self.request.refresh_from_db()
        assert self.request.status == CompanyRequest.RequestState.REJECTED

    def test_reject_request_already_processed(self):
        self.client.force_authenticate(user=self.receiver)
        self.request.status = CompanyRequest.RequestState.REJECTED
        self.request.save()
        url = f'/api/v1/requests/{self.request.pk}/reject/'
        response = self.client.patch(url)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_cancel_request_success(self):
        self.client.force_authenticate(user=self.sender)
        url = f'/api/v1/requests/{self.request.pk}/cancel/'
        response = self.client.patch(url)
        assert response.status_code == status.HTTP_200_OK
        self.request.refresh_from_db()
        assert self.request.status == CompanyRequest.RequestState.CANCELLED

    def test_cancel_request_by_non_sender(self):
        self.client.force_authenticate(user=self.receiver)
        url = f'/api/v1/requests/{self.request.pk}/cancel/'
        response = self.client.patch(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        self.request.refresh_from_db()
        assert self.request.status == CompanyRequest.RequestState.PENDING
        
    def test_cancel_request_already_processed(self):
        self.client.force_authenticate(user=self.sender)
        self.request.status = CompanyRequest.RequestState.APPROVED
        self.request.save()
        url = f'/api/v1/requests/{self.request.pk}/cancel/'
        response = self.client.patch(url)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        
    def test_cancel_request_not_found(self):
        self.client.force_authenticate(user=self.sender)
        url = '/api/v1/requests/999/cancel/'
        response = self.client.patch(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND
        
    def test_request_invitation_permission_denied(self):
        self.client.force_authenticate(user=self.sender)
        url = f'/api/v1/requests/{self.request.pk}/'
        response = self.client.delete(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        
    def test_update_request_not_allowed(self):
        self.client.force_authenticate(user=self.receiver)
        updated_data = {
            "status": CompanyRequest.RequestState.APPROVED,
        }
        url = f'/api/v1/requests/{self.request.pk}/'
        response = self.client.patch(url, updated_data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        
    def test_destroy_request_permission_denied(self):
        self.client.force_authenticate(user=self.receiver)
        url = f'/api/v1/requests/{self.request.pk}/'
        response = self.client.delete(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_list_user_requests(self):
        self.client.force_authenticate(user=self.sender)
        url = '/api/v1/requests/user-requests/'
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert len(response_data) == 1
        assert response_data[0]['id'] == self.request.id
        
    def test_list_user_requests_no_requests(self):
        self.client.force_authenticate(user=self.other_user)
        url = '/api/v1/requests/user-requests/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), [])

    def test_list_owner_requests(self):
        self.client.force_authenticate(user=self.receiver)
        url = '/api/v1/requests/'
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert len(response_data) == 1
        assert response_data[0]['id'] == self.request.id
        
    def test_list_owner_requests_no_requests(self):
        self.client.force_authenticate(user=self.other_user)
        url = '/api/v1/requests/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), [])
        

class CompanyRequestSerializerTests(APITestCase):

    def setUp(self):
        self.sender = User.objects.create_user(
            username="sender", 
            password="1Qaz_2wsx_3edc", 
            email="sender@example.com"
        )
        self.receiver = User.objects.create_user(
            username="receiver", 
            password="1Qaz_2wsx_3edc", 
            email="receiver@example.com"
        )
        self.company = Company.objects.create(
            name="TestCompany", 
            description="Test description", 
            owner=self.receiver, 
            visibility=Company.Visibility.VISIBLE
        )
        
    def test_create_request_success(self):
        self.client.force_authenticate(user=self.sender)
        data = {'company': self.company.pk}
        url = '/api/v1/requests/'
        response = self.client.post(url, data)
        assert response.status_code == status.HTTP_201_CREATED
        request_obj = CompanyRequest.objects.last()
        assert request_obj.sender == self.sender
        assert request_obj.receiver == self.receiver
        assert request_obj.company == self.company
        assert request_obj.status == CompanyRequest.RequestState.PENDING

    def test_create_request_user_already_member(self):
        CompanyMember.objects.create(user=self.sender, company=self.company)
        self.client.force_authenticate(user=self.sender)
        data = {'company': self.company.pk}
        url = '/api/v1/requests/'
        response = self.client.post(url, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_request_already_processed(self):
        CompanyRequest.objects.create(
            sender=self.sender, 
            receiver=self.receiver, 
            company=self.company, 
            status=CompanyRequest.RequestState.PENDING)
        self.client.force_authenticate(user=self.sender)
        data = {'company': self.company.pk}
        url = '/api/v1/requests/'
        response = self.client.post(url, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        
        
class CompanyMemberViewSetTests(APITestCase):

    def setUp(self):
        self.owner = User.objects.create_user(
            username="owner", 
            password="1Qaz_2wsx_3edc", 
            email="owner@example.com"
        )
        self.member = User.objects.create_user(
            username="member", 
            password="1Qaz_2wsx_3edc", 
            email="member@example.com"
        )

        self.other_user = User.objects.create_user(
            username="other_user", 
            password="1Qaz_2wsx_3edc", 
            email="other_user@example.com"
        )
        
        self.company = Company.objects.create(
            name="TestCompany", 
            description="Test description", 
            owner=self.owner,
            visibility=Company.Visibility.VISIBLE
        )
        self.company2 = Company.objects.create(
            name="TestCompany", 
            description="Test description", 
            owner=self.owner,
            visibility=Company.Visibility.HIDDEN
        )
        CompanyMember.objects.create(user=self.owner, company=self.company)
        CompanyMember.objects.create(user=self.member, company=self.company)
        CompanyMember.objects.create(user=self.owner, company=self.company2)
        CompanyMember.objects.create(user=self.member, company=self.company2)

    def test_leave_company_success(self):
        self.client.force_authenticate(user=self.member)
        data = {'company': self.company.id}
        url = '/api/v1/company-members/leave/'
        response = self.client.delete(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(CompanyMember.objects.filter(user=self.member, company=self.company).exists())

    def test_leave_company_permission_denied(self):
        self.client.force_authenticate(user=self.other_user)
        data = {'company': self.company.id}
        url = '/api/v1/company-members/leave/'
        response = self.client.delete(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
    def test_leave_company_owner(self):
        self.client.force_authenticate(user=self.owner)
        data = {'company': self.company.id}
        url = '/api/v1/company-members/leave/'
        response = self.client.delete(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
    def test_kick_from_company_success(self):
        self.client.force_authenticate(user=self.owner)
        data = {'company': self.company.id, 'user': self.member.id}
        url = '/api/v1/company-members/kick/'
        response = self.client.delete(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertFalse(CompanyMember.objects.filter(user=self.member, company=self.company).exists())

    def test_kick_from_company_not_owner(self):
        self.client.force_authenticate(user=self.member)
        data = {'company': self.company.id, 'user': self.member.id}
        url = '/api/v1/company-members/kick/'
        response = self.client.delete(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)        
        
    def test_kick_from_company_missing_data(self):
        self.client.force_authenticate(user=self.owner)
        data = {'company': self.company.id}
        url = '/api/v1/company-members/kick/'
        response = self.client.delete(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
    def test_kick_from_company_kick_owner(self):
        self.client.force_authenticate(user=self.owner)
        data = {'company': self.company.id, 'user': self.owner.id}
        url = '/api/v1/company-members/kick/'
        response = self.client.delete(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
    def test_kick_from_company_user_not_member(self):
        self.client.force_authenticate(user=self.owner)
        data = {'company': self.company.id, 'user': self.other_user.id}
        url = '/api/v1/company-members/kick/'
        response = self.client.delete(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        
    def test_appoint_admin_success(self):
        self.client.force_authenticate(user=self.owner)
        data = {'company': self.company.id, 'user': self.member.id}
        url = '/api/v1/company-members/appoint-admin/' 
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        membership = CompanyMember.objects.get(user=self.member, company=self.company)
        self.assertEqual(membership.role, CompanyMember.Role.ADMIN)

    def test_appoint_admin_already_admin(self):
        self.client.force_authenticate(user=self.owner)
        data = {'company': self.company.id, 'user': self.member.id}
        url = '/api/v1/company-members/appoint-admin/'
        self.client.patch(url, data, format='json')
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_appoint_admin_not_member(self):
        self.client.force_authenticate(user=self.owner)
        data = {'company': self.company.id, 'user': self.other_user.id} 
        url = '/api/v1/company-members/appoint-admin/'
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_appoint_admin_permission_denied(self):
        self.client.force_authenticate(user=self.member)
        data = {'company': self.company.id, 'user': self.other_user.id}
        url = '/api/v1/company-members/appoint-admin/'
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_remove_admin_success(self):
        self.client.force_authenticate(user=self.owner)
        data = {'company': self.company.id, 'user': self.member.id}
        url = '/api/v1/company-members/appoint-admin/'
        self.client.patch(url, data, format='json')
        data = {'company': self.company.id, 'user': self.member.id}
        url = '/api/v1/company-members/remove-admin/'
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        membership = CompanyMember.objects.get(user=self.member, company=self.company)
        self.assertEqual(membership.role, CompanyMember.Role.MEMBER)

    def test_remove_admin_not_admin(self):
        self.client.force_authenticate(user=self.owner)
        data = {'company': self.company.id, 'user': self.member.id}
        url = '/api/v1/company-members/remove-admin/'
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_remove_admin_permission_denied(self):
        self.client.force_authenticate(user=self.member)
        data = {'company': self.company.id, 'user': self.owner.id}
        url = '/api/v1/company-members/remove-admin/'
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_members_success(self):
        self.client.force_authenticate(user=self.owner)
        url = '/api/v1/company-members/members/?company=' + str(self.company.id)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)  
        
    def test_list_members_success_company_hidden(self):
        self.client.force_authenticate(user=self.owner)
        url = '/api/v1/company-members/members/?company=' + str(self.company2.id)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)  

    def test_list_members_empty(self):
        self.client.force_authenticate(user=self.other_user)
        url = '/api/v1/company-members/members/?company=' + str(self.company2.id)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), [])
        
    def test_create_company_member_not_allowed(self):
        self.client.force_authenticate(user=self.owner)
        data = {'user': self.owner.id, 'company': self.company.id}
        url = '/api/v1/company-members/'
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_not_available(self):
        self.client.force_authenticate(user=self.member)
        url = '/api/v1/company-members/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
    def test_destroy_not_allowed(self):
        self.client.force_authenticate(user=self.member)
        url = f'/api/v1/company-members/{self.member.id}/' 
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_is_member_of_company_success(self):
        self.client.force_authenticate(user=self.member)
        url = f'/api/v1/company-members/member-role/?company={self.company.id}'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["role"], CompanyMember.Role.MEMBER)
        
    def test_is_member_of_company_not_member(self):
        self.client.force_authenticate(user=self.other_user)
        url = f'/api/v1/company-members/member-role/?company={self.company.id}'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data["role"]) 
        
    def test_is_member_of_company_no_company_id(self):
        self.client.force_authenticate(user=self.member)
        url = '/api/v1/company-members/member-role/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
    def test_user_memberships_success(self):
        self.client.force_authenticate(user=self.member)
        url = '/api/v1/company-members/user-memberships/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        company_data = response.data
        self.assertTrue(len(company_data) > 0)
        for company in company_data:
            self.assertIn('company', company)
            self.assertIn('company__name', company)
            
    def test_user_memberships_no_companies(self):
        self.client.force_authenticate(user=self.other_user)
        url = '/api/v1/company-members/user-memberships/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        print(response.data)
        self.assertEqual(list(response.data), [])
        