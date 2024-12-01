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
        # auth receiver1
        self.client.force_authenticate(user=self.receiver1)
        
        # invite1 accept
        url = f'/api/v1/invitations/{self.invitation1.pk}/accept/'
        response = self.client.patch(url)
        assert response.status_code == status.HTTP_200_OK
        
        # check invitation status
        self.invitation1.refresh_from_db()
        assert self.invitation1.status == CompanyInvitation.InvitationState.ACCEPTED
        
        # check company member
        assert CompanyMember.objects.filter(user=self.receiver1, company=self.company1).exists()

    def test_accept_invitation_already_processed(self):
        # auth receiver1
        self.client.force_authenticate(user=self.receiver1)
        
        # update status to ACCEPTED
        self.invitation1.status = CompanyInvitation.InvitationState.ACCEPTED
        self.invitation1.save()

        # invite1 accept again
        url = f'/api/v1/invitations/{self.invitation1.pk}/accept/'
        response = self.client.patch(url)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        
    def test_accept_invitation_by_non_receiver(self):
        # auth owner 
        self.client.force_authenticate(user=self.owner)     
        
        # try to accept as owner
        url = f'/api/v1/invitations/{self.invitation1.pk}/accept/'
        response = self.client.patch(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        
        # check invitation status did not change
        self.invitation1.refresh_from_db()
        assert self.invitation1.status == CompanyInvitation.InvitationState.PENDING
        
    def test_accept_invitation_not_found(self):
        # auth receiver1
        self.client.force_authenticate(user=self.receiver1)
        
        # try to accept a non-existent invitation
        url = '/api/v1/invitations/999/accept/'
        response = self.client.patch(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND
        
    def test_decline_invitation_success(self):
        # auth receiver1
        self.client.force_authenticate(user=self.receiver1)
        
        # decline invite1
        url = f'/api/v1/invitations/{self.invitation1.pk}/decline/'
        response = self.client.patch(url)
        assert response.status_code == status.HTTP_200_OK

        # check invitation status
        self.invitation1.refresh_from_db()
        assert self.invitation1.status == CompanyInvitation.InvitationState.DECLINED

    def test_decline_invitation_already_processed(self):
        # auth receiver1
        self.client.force_authenticate(user=self.receiver1)
        
        # update status to DECLINED
        self.invitation1.status = CompanyInvitation.InvitationState.DECLINED
        self.invitation1.save()

        # try to decline again
        url = f'/api/v1/invitations/{self.invitation1.pk}/decline/'
        response = self.client.patch(url)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        

    def test_decline_invitation_by_non_receiver(self):
        # auth owner
        self.client.force_authenticate(user=self.owner)     
        
        # try to decline as owner
        url = f'/api/v1/invitations/{self.invitation1.pk}/decline/'
        response = self.client.patch(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        
        # check invitation status did not change
        self.invitation1.refresh_from_db()
        assert self.invitation1.status == CompanyInvitation.InvitationState.PENDING
        
    def test_decline_invitation_not_found(self):
        # auth receiver1
        self.client.force_authenticate(user=self.receiver1)
        
        # try to decline a non-existent invitation
        url = '/api/v1/invitations/999/decline/'
        response = self.client.patch(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_revoke_invitation_success(self):
        # auth receiver1
        self.client.force_authenticate(user=self.owner)
        
        # revoke invite1
        url = f'/api/v1/invitations/{self.invitation1.pk}/revoke/'
        response = self.client.patch(url)
        assert response.status_code == status.HTTP_200_OK

        # check invitation status
        self.invitation1.refresh_from_db()
        assert self.invitation1.status == CompanyInvitation.InvitationState.REVOKED

    def test_revoke_invitation_by_non_owner(self):
        # auth receiver
        self.client.force_authenticate(user=self.receiver1)        
        # try to revoke as non-owner
        url = f'/api/v1/invitations/{self.invitation1.pk}/revoke/'
        response = self.client.patch(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        
        # check invitation status did not change
        self.invitation1.refresh_from_db()
        assert self.invitation1.status == CompanyInvitation.InvitationState.PENDING
        
    def test_revoke_invitation_already_processed(self):
        # auth owner
        self.client.force_authenticate(user=self.owner)
        
        # update status to ACCEPTED
        self.invitation1.status = CompanyInvitation.InvitationState.ACCEPTED
        self.invitation1.save()
        assert self.invitation1.status == CompanyInvitation.InvitationState.ACCEPTED
        
        # try to revoke an already processed invitation
        url = f'/api/v1/invitations/{self.invitation1.pk}/revoke/'
        response = self.client.patch(url)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        
    def test_update_invitation_not_allowed(self):
        # Authenticate as sender
        self.client.force_authenticate(user=self.owner)

        # Prepare data for updating the invitation
        updated_data = {
            "status": CompanyInvitation.InvitationState.ACCEPTED,
        }

        # Try to directly update the invitation
        url = f'/api/v1/invitations/{self.invitation1.pk}/'
        response = self.client.patch(url, updated_data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        
    def test_destroy_invitation_permission_denied(self):
        # auth receiver1
        self.client.force_authenticate(user=self.receiver1)
        
        # try to delete an invitation
        url = f'/api/v1/invitations/{self.invitation1.pk}/'
        response = self.client.delete(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN    
        
    def test_list_user_invitations(self):
        # auth receiver
        self.client.force_authenticate(user=self.receiver1)

        # send GET request
        url = '/api/v1/invitations/user-invitations/'
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK

        # check response contains the correct invitation for receiver1
        response_data = response.json()
        assert len(response_data) == 1  # Only 1 invitation for receiver1
        assert response_data[0]['id'] == self.invitation1.id
        
    def test_list_user_invitations_no_invitations(self):
        # Authenticate as a user who has no invitations
        self.client.force_authenticate(user=self.other_user)

        # Send GET request to get user's invitations
        url = '/api/v1/invitations/user-invitations/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify the response contains an empty list, as the user has no invitations
        self.assertEqual(response.json(), [])

    def test_list_owner_invitations(self):
        # auth sender
        self.client.force_authenticate(user=self.owner)

        # send GET request
        url = '/api/v1/invitations/'
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK

        # check response contains correct invitations
        response_data = response.json()
        assert len(response_data) == 2
        assert response_data[0]['id'] == self.invitation1.id
        assert response_data[1]['id'] == self.invitation2.id

    def test_list_owner_invitations_no_invitations(self):
        # Authenticate as the owner (who has no invitations)
        self.client.force_authenticate(user=self.other_user)

        # Send GET request to list invitations
        url = '/api/v1/invitations/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify the response contains an empty list, as the owner has no invitations
        self.assertEqual(response.json(), [])

        
class CompanyInvitationSerializerTests(APITestCase):

    def setUp(self):
        # Create users for testing
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
        
        # Create companies for testing
        self.company1 = Company.objects.create(
            name="Test1", 
            description="Test description", 
            owner=self.owner,  
            visibility=Company.Visibility.VISIBLE  
        )
        
    def test_create_invitation_success(self):
        # Log in as owner
        self.client.force_authenticate(user=self.owner)     
        data = {
            'receiver': self.receiver1.pk,
            'company': self.company1.pk
        }
        
        # Send POST request
        url = '/api/v1/invitations/'
        response = self.client.post(url, data)
        
        # Check status 
        assert response.status_code == status.HTTP_201_CREATED
        
        # Verify invitation data
        invitation = CompanyInvitation.objects.last()
        assert invitation.sender == self.owner
        assert invitation.receiver == self.receiver1
        assert invitation.company == self.company1
        assert invitation.status == CompanyInvitation.InvitationState.PENDING

    def test_create_invitation_user_already_member(self):
        # Add receiver1 as a member of company1
        CompanyMember.objects.create(user=self.receiver1, company=self.company1)
        
        # Log in as owner
        self.client.force_authenticate(user=self.owner)
        data = {
            'receiver': self.receiver1.pk,
            'company': self.company1.pk
        }
        
        # Send POST request to create an invitation
        url = '/api/v1/invitations/'
        response = self.client.post(url, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        
    def test_create_invitation_already_processed(self):
        # Create an existing invitation
        self.client.force_authenticate(user=self.owner)
        existing_invitation = CompanyInvitation.objects.create( # noqa: F841
            sender=self.owner,
            receiver=self.receiver1,
            company=self.company1,
            status=CompanyInvitation.InvitationState.PENDING
        )
        data = {
            'receiver': self.receiver1.pk,
            'company': self.company1.pk
        }
        
        # Send POST request to create a new invitation
        url = '/api/v1/invitations/'
        response = self.client.post(url, data)
        
        # Check status 
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    
class CompanyRequestViewSetTests(APITestCase):

    def setUp(self):
        # Create users for testing
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
        
        # Create company for testing
        self.company = Company.objects.create(
            name="TestCompany", 
            description="Test description", 
            owner=self.receiver, 
            visibility=Company.Visibility.VISIBLE
        )
        
        # Create a request
        self.request = CompanyRequest.objects.create(
            sender=self.sender,
            receiver=self.receiver,
            company=self.company,
            status=CompanyRequest.RequestState.PENDING
        )

    def test_approve_request_success(self):
        # Authenticate as receiver
        self.client.force_authenticate(user=self.receiver)

        # approve request
        url = f'/api/v1/requests/{self.request.pk}/approve/'
        response = self.client.patch(url)
        assert response.status_code == status.HTTP_200_OK

        # Verify request status is updated
        self.request.refresh_from_db()
        assert self.request.status == CompanyRequest.RequestState.APPROVED

        # Verify company member is added
        assert CompanyMember.objects.filter(user=self.sender, company=self.company).exists()

    def test_approve_request_already_processed(self):
        # Authenticate as receiver
        self.client.force_authenticate(user=self.receiver)

        # Update request status to approved
        self.request.status = CompanyRequest.RequestState.APPROVED
        self.request.save()

        # Try to accept the already processed request
        url = f'/api/v1/requests/{self.request.pk}/approve/'
        response = self.client.patch(url)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_approve_request_by_non_receiver(self):
        # Authenticate as sender
        self.client.force_authenticate(user=self.sender)

        # Try to approve request as sender
        url = f'/api/v1/requests/{self.request.pk}/approve/'
        response = self.client.patch(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

        # Verify request status remains unchanged
        self.request.refresh_from_db()
        assert self.request.status == CompanyRequest.RequestState.PENDING

    def test_reject_request_success(self):
        # Authenticate as receiver
        self.client.force_authenticate(user=self.receiver)

        # reject request
        url = f'/api/v1/requests/{self.request.pk}/reject/'
        response = self.client.patch(url)
        assert response.status_code == status.HTTP_200_OK

        # Verify request status is updated
        self.request.refresh_from_db()
        assert self.request.status == CompanyRequest.RequestState.REJECTED

    def test_reject_request_already_processed(self):
        # Authenticate as receiver
        self.client.force_authenticate(user=self.receiver)

        # Update request status to rejected
        self.request.status = CompanyRequest.RequestState.REJECTED
        self.request.save()

        # Try to reject the already processed request
        url = f'/api/v1/requests/{self.request.pk}/reject/'
        response = self.client.patch(url)

        # Check response status
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_cancel_request_success(self):
        # Authenticate as sender
        self.client.force_authenticate(user=self.sender)

        # Cancel request
        url = f'/api/v1/requests/{self.request.pk}/cancelled/'
        response = self.client.patch(url)
        assert response.status_code == status.HTTP_200_OK

        # Verify request status is updated
        self.request.refresh_from_db()
        assert self.request.status == CompanyRequest.RequestState.CANCELLED

    def test_cancel_request_by_non_sender(self):
        # Authenticate as receiver
        self.client.force_authenticate(user=self.receiver)

        # Try to cancel request as receiver
        url = f'/api/v1/requests/{self.request.pk}/cancelled/'
        response = self.client.patch(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

        # Verify request status remains unchanged
        self.request.refresh_from_db()
        assert self.request.status == CompanyRequest.RequestState.PENDING
        
    def test_cancel_request_already_processed(self):
        # Authenticate as sender
        self.client.force_authenticate(user=self.sender)

        # Update request status to a processed state 
        self.request.status = CompanyRequest.RequestState.APPROVED
        self.request.save()

        # Try to cancel the processed request
        url = f'/api/v1/requests/{self.request.pk}/cancelled/'
        response = self.client.patch(url)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        
    def test_cancel_request_not_found(self):
        # Authenticate as sender
        self.client.force_authenticate(user=self.sender)

        # Try to cancel a non-existent request
        url = '/api/v1/requests/999/cancelled/'
        response = self.client.patch(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND
        
    def test_request_invitation_permission_denied(self):
        # Authenticate as a user without permission
        self.client.force_authenticate(user=self.sender)

        # Try to delete an invitation
        url = f'/api/v1/requests/{self.request.pk}/'
        response = self.client.delete(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        
    def test_update_request_not_allowed(self):
        # Authenticate as sender
        self.client.force_authenticate(user=self.receiver)

        # Prepare data for updating the request
        updated_data = {
            "status": CompanyRequest.RequestState.APPROVED,
        }

        # Try to directly update the request
        url = f'/api/v1/requests/{self.request.pk}/'
        response = self.client.patch(url, updated_data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        
    def test_destroy_request_permission_denied(self):
        # Authenticate as a user without permission
        self.client.force_authenticate(user=self.receiver)

        # Try to delete a request
        url = f'/api/v1/requests/{self.request.pk}/'
        response = self.client.delete(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_list_user_requests(self):
        # Authenticate as sender
        self.client.force_authenticate(user=self.sender)

        # Send GET request
        url = '/api/v1/requests/user-requests/'
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK

        # Verify response contains the correct request
        response_data = response.json()
        assert len(response_data) == 1
        assert response_data[0]['id'] == self.request.id
        
    def test_list_user_requests_no_requests(self):
        # Authenticate as a user who has no requests
        self.client.force_authenticate(user=self.other_user)

        # Send GET request to get user's requests
        url = '/api/v1/requests/user-requests/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify the response contains an empty list, as the user has no requests
        self.assertEqual(response.json(), [])

    def test_list_owner_requests(self):
        # Authenticate as receiver
        self.client.force_authenticate(user=self.receiver)

        # Send GET request
        url = '/api/v1/requests/'
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK

        # Verify response contains the correct request
        response_data = response.json()
        assert len(response_data) == 1
        assert response_data[0]['id'] == self.request.id
        
    def test_list_owner_requests_no_requests(self):
        # Authenticate as the owner (who has no requests)
        self.client.force_authenticate(user=self.other_user)

        # Send GET request to list requests
        url = '/api/v1/requests/'
        response = self.client.get(url)

        # Check that response status is 200 OK
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify the response contains an empty list, as the owner has no requests
        self.assertEqual(response.json(), [])
        

class CompanyRequestSerializerTests(APITestCase):

    def setUp(self):
        # Сreate users for testing
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
        
        # Сreate a company for testing
        self.company = Company.objects.create(
            name="TestCompany", 
            description="Test description", 
            owner=self.receiver,  
            visibility=Company.Visibility.VISIBLE
        )
        

    def test_create_request_success(self):
        # auth sender
        self.client.force_authenticate(user=self.sender)
        data = {'company': self.company.pk}

        # send POST request
        url = '/api/v1/requests/'
        response = self.client.post(url, data)
        assert response.status_code == status.HTTP_201_CREATED

        # verify request data
        request_obj = CompanyRequest.objects.last()
        assert request_obj.sender == self.sender
        assert request_obj.receiver == self.receiver
        assert request_obj.company == self.company
        assert request_obj.status == CompanyRequest.RequestState.PENDING

    def test_create_request_user_already_member(self):
        # add sender as member
        CompanyMember.objects.create(user=self.sender, company=self.company)

        # auth sender
        self.client.force_authenticate(user=self.sender)
        data = {'company': self.company.pk}

        # send POST request
        url = '/api/v1/requests/'
        response = self.client.post(url, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_request_already_processed(self):
        # create existing request
        CompanyRequest.objects.create(
            sender=self.sender, 
            receiver=self.receiver, 
            company=self.company, 
            status=CompanyRequest.RequestState.PENDING)

        # auth sender
        self.client.force_authenticate(user=self.sender)
        data = {'company': self.company.pk}

        # send POST request
        url = '/api/v1/requests/'
        response = self.client.post(url, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        
        
class CompanyMemberViewSetTests(APITestCase):

    def setUp(self):
        # Create users
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
        
        # Create company 
        self.company = Company.objects.create(
            name="TestCompany", 
            description="Test description", 
            owner=self.owner,
            visibility=Company.Visibility.VISIBLE
        )
        # Create  hidden company 
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
        # Auth as member
        self.client.force_authenticate(user=self.member)
        data = {'company': self.company.id}

        # Send DELETE request to leave company
        url = '/api/v1/company-members/leave/'
        response = self.client.delete(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify member left
        self.assertFalse(CompanyMember.objects.filter(user=self.member, company=self.company).exists())

    def test_leave_company_permission_denied(self):
        # Auth as non-member
        self.client.force_authenticate(user=self.other_user)
        data = {'company': self.company.id}

        # Send DELETE request to leave company
        url = '/api/v1/company-members/leave/'
        response = self.client.delete(url, data, format='json')

        # Check permission denied
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
    def test_leave_company_owner(self):
        # Auth as owner
        self.client.force_authenticate(user=self.owner)
        data = {'company': self.company.id}

        # Send DELETE request to leave company
        url = '/api/v1/company-members/leave/'
        response = self.client.delete(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
    def test_kick_from_company_success(self):
        # Auth as owner
        self.client.force_authenticate(user=self.owner)
        data = {'company': self.company.id, 'user': self.member.id}

        # Send DELETE request to kick member
        url = '/api/v1/company-members/kick/'
        response = self.client.delete(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify member was kicked
        self.assertFalse(CompanyMember.objects.filter(user=self.member, company=self.company).exists())

    def test_kick_from_company_not_owner(self):
        # Auth as member
        self.client.force_authenticate(user=self.member)
        data = {'company': self.company.id, 'user': self.member.id}

        # Send DELETE request to kick member
        url = '/api/v1/company-members/kick/'
        response = self.client.delete(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)        
        
    def test_kick_from_company_missing_data(self):
        # Auth as owner
        self.client.force_authenticate(user=self.owner)
        data = {'company': self.company.id}  # Missing user ID

        # Send DELETE request to kick member without user ID
        url = '/api/v1/company-members/kick/'
        response = self.client.delete(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
    def test_kick_from_company_kick_owner(self):
        # Auth as owner
        self.client.force_authenticate(user=self.owner)
        data = {'company': self.company.id, 'user': self.owner.id}

        # Send DELETE request to kick owner
        url = '/api/v1/company-members/kick/'
        response = self.client.delete(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
    def test_kick_from_company_user_not_member(self):
        # Auth as owner
        self.client.force_authenticate(user=self.owner)
        data = {'company': self.company.id, 'user': self.other_user.id}  # Non-member user

        # Send DELETE request to kick non-member user
        url = '/api/v1/company-members/kick/'
        response = self.client.delete(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        
    def test_appoint_admin_success(self):
        # Auth as owner
        self.client.force_authenticate(user=self.owner)
        data = {'company': self.company.id, 'user': self.member.id}

        # Send request to appoint admin
        url = '/api/v1/company-members/appoint-admin/' 
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify the member is now an admin
        membership = CompanyMember.objects.get(user=self.member, company=self.company)
        self.assertEqual(membership.role, CompanyMember.Role.ADMIN)

    def test_appoint_admin_already_admin(self):
        #make the member an admin
        self.client.force_authenticate(user=self.owner)
        data = {'company': self.company.id, 'user': self.member.id}
        url = '/api/v1/company-members/appoint-admin/'
        self.client.patch(url, data, format='json')
        
        # Send PATCH request to appoint admin
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_appoint_admin_not_member(self):
        # Auth as owner
        self.client.force_authenticate(user=self.owner)
        data = {'company': self.company.id, 'user': self.other_user.id}  # Non-member 

        # Send PATCH request to appoint admin
        url = '/api/v1/company-members/appoint-admin/'
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_appoint_admin_permission_denied(self):
        # Auth as member
        self.client.force_authenticate(user=self.member)
        data = {'company': self.company.id, 'user': self.other_user.id}

        # Send PATCH request to appoint admin
        url = '/api/v1/company-members/appoint-admin/'
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_remove_admin_success(self):
        #make the member an admin
        self.client.force_authenticate(user=self.owner)
        data = {'company': self.company.id, 'user': self.member.id}
        url = '/api/v1/company-members/appoint-admin/'
        self.client.patch(url, data, format='json')

        # try to remove the admin
        data = {'company': self.company.id, 'user': self.member.id}
        url = '/api/v1/company-members/remove-admin/'
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify the admin role is removed
        membership = CompanyMember.objects.get(user=self.member, company=self.company)
        self.assertEqual(membership.role, CompanyMember.Role.MEMBER)

    def test_remove_admin_not_admin(self):
        # Auth as owner, but try to remove non-admin
        self.client.force_authenticate(user=self.owner)
        data = {'company': self.company.id, 'user': self.member.id}

        # Send POST request to remove admin
        url = '/api/v1/company-members/remove-admin/'
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_remove_admin_permission_denied(self):
        # Auth as member
        self.client.force_authenticate(user=self.member)
        data = {'company': self.company.id, 'user': self.owner.id}  # Member trying to remove owner

        # Send POST request to remove admin
        url = '/api/v1/company-members/remove-admin/'
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_members_success(self):
        # Auth as owner
        self.client.force_authenticate(user=self.owner)

        # Send GET request to list members
        url = '/api/v1/company-members/members/?company=' + str(self.company.id)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check number of members
        self.assertEqual(len(response.data), 2)  
        
    def test_list_members_success_company_hidden(self):
        # Auth as owner
        self.client.force_authenticate(user=self.owner)

        # Send GET request to list members
        url = '/api/v1/company-members/members/?company=' + str(self.company2.id)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check number of members
        self.assertEqual(len(response.data), 2)  

    def test_list_members_permission_denied(self):
        # Auth as non-member
        self.client.force_authenticate(user=self.other_user)

        # Send GET request to list members
        url = '/api/v1/company-members/members/?company=' + str(self.company2.id)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
    def test_create_company_member_not_allowed(self):
        # Authenticate as user
        self.client.force_authenticate(user=self.owner)

        # Prepare data to create a company member
        data = {'user': self.owner.id, 'company': self.company.id}

        # Try to directly create a company member
        url = '/api/v1/company-members/'
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_not_available(self):
        # Auth as member
        self.client.force_authenticate(user=self.member)

        # Send GET request to list members
        url = '/api/v1/company-members/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
    def test_destroy_not_allowed(self):
        # Auth as member
        self.client.force_authenticate(user=self.member)

        # Send DELETE request to destroy a member
        url = f'/api/v1/company-members/{self.member.id}/' 
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_is_member_of_company_success(self):
        # Auth as member
        self.client.force_authenticate(user=self.member)

        # Send GET request to check if user is a member of the company
        url = f'/api/v1/company-members/is-member/?company={self.company.id}'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["is_member"], True)
        
    def test_is_member_of_company_not_member(self):
        # Auth as non-member
        self.client.force_authenticate(user=self.other_user)

        # Send GET request to check if user is a member of the company
        url = f'/api/v1/company-members/is-member/?company={self.company.id}'
        response = self.client.get(url)

        # Check response status and data
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["is_member"], False)
        
    def test_is_member_of_company_no_company_id(self):
        # Auth as member
        self.client.force_authenticate(user=self.member)

        # Send GET request without company ID
        url = '/api/v1/company-members/is-member/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
    def test_user_memberships_success(self):
        # Auth as a user with memberships
        self.client.force_authenticate(user=self.member)

        # Send GET request to retrieve user memberships
        url = '/api/v1/company-members/user-memberships/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify that the response contains the companies the user is a member of
        company_data = response.data
        self.assertTrue(len(company_data) > 0)
        for company in company_data:
            self.assertIn('company', company)
            self.assertIn('company__name', company)
            
    def test_user_memberships_no_companies(self):
        # Auth as a user with no memberships
        self.client.force_authenticate(user=self.other_user)

        # Send GET request to retrieve user memberships
        url = '/api/v1/company-members/user-memberships/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        print(response.data)
        # Verify the response contains an empty list, as the user has no memberships
        self.assertEqual(list(response.data), [])
        