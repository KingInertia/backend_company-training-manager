from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.companies.enums import RequestState, Visibility
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
            visibility=Visibility.VISIBLE  
        )
        
        
        self.invitation1 = CompanyInvitation.objects.create(
            company=self.company1,
            sender=self.owner,
            receiver=self.receiver1,
            status=RequestState.PENDING
        )
        self.invitation2 = CompanyInvitation.objects.create(
            company=self.company1,
            sender=self.owner,
            receiver=self.receiver2,
            status=RequestState.PENDING
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
        assert self.invitation1.status == RequestState.ACCEPTED
        
        # check company member
        assert CompanyMember.objects.filter(user=self.receiver1, company=self.company1).exists()

    def test_accept_invitation_already_processed(self):
        # auth receiver1
        self.client.force_authenticate(user=self.receiver1)
        
        # update status to ACCEPTED
        self.invitation1.status = RequestState.ACCEPTED
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
        assert self.invitation1.status == RequestState.PENDING
        
    def test_decline_invitation_success(self):
        # auth receiver1
        self.client.force_authenticate(user=self.receiver1)
        
        # decline invite1
        url = f'/api/v1/invitations/{self.invitation1.pk}/decline/'
        response = self.client.patch(url)
        assert response.status_code == status.HTTP_200_OK

        # check invitation status
        self.invitation1.refresh_from_db()
        assert self.invitation1.status == RequestState.DECLINED

    def test_decline_invitation_already_processed(self):
        # auth receiver1
        self.client.force_authenticate(user=self.receiver1)
        
        # update status to DECLINED
        self.invitation1.status = RequestState.DECLINED
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
        assert self.invitation1.status == RequestState.PENDING

    def test_cancel_invitation_by_non_owner(self):
        # auth receiver
        self.client.force_authenticate(user=self.receiver1)        
        # try to cancel as non-owner
        url = f'/api/v1/invitations/{self.invitation1.pk}/cancelled/'
        response = self.client.patch(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        
        # check invitation status did not change
        self.invitation1.refresh_from_db()
        assert self.invitation1.status == RequestState.PENDING
        
    def test_cancel_invitation_already_processed(self):
        # auth owner
        self.client.force_authenticate(user=self.owner)
        
        # update status to ACCEPTED
        self.invitation1.status = RequestState.ACCEPTED
        self.invitation1.save()
        assert self.invitation1.status == RequestState.ACCEPTED
        # try to cancel an already processed invitation
        url = f'/api/v1/invitations/{self.invitation1.pk}/cancelled/'
        response = self.client.patch(url)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        
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
            visibility=Visibility.VISIBLE  
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
        assert invitation.status == RequestState.PENDING

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
            status=RequestState.PENDING
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
        
        # Create company for testing
        self.company = Company.objects.create(
            name="TestCompany", 
            description="Test description", 
            owner=self.receiver,  
            visibility=Visibility.VISIBLE
        )
        
        # Create a request
        self.request = CompanyRequest.objects.create(
            sender=self.sender,
            receiver=self.receiver,
            company=self.company,
            status=RequestState.PENDING
        )

    def test_accept_request_success(self):
        # Authenticate as receiver
        self.client.force_authenticate(user=self.receiver)

        # Accept request
        url = f'/api/v1/requests/{self.request.pk}/accept/'
        response = self.client.patch(url)
        assert response.status_code == status.HTTP_200_OK

        # Verify request status is updated
        self.request.refresh_from_db()
        assert self.request.status == RequestState.ACCEPTED

        # Verify company member is added
        assert CompanyMember.objects.filter(user=self.sender, company=self.company).exists()

    def test_accept_request_already_processed(self):
        # Authenticate as receiver
        self.client.force_authenticate(user=self.receiver)

        # Update request status to ACCEPTED
        self.request.status = RequestState.ACCEPTED
        self.request.save()

        # Try to accept the already processed request
        url = f'/api/v1/requests/{self.request.pk}/accept/'
        response = self.client.patch(url)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_accept_request_by_non_receiver(self):
        # Authenticate as sender
        self.client.force_authenticate(user=self.sender)

        # Try to accept request as sender
        url = f'/api/v1/requests/{self.request.pk}/accept/'
        response = self.client.patch(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

        # Verify request status remains unchanged
        self.request.refresh_from_db()
        assert self.request.status == RequestState.PENDING

    def test_decline_request_success(self):
        # Authenticate as receiver
        self.client.force_authenticate(user=self.receiver)

        # Decline request
        url = f'/api/v1/requests/{self.request.pk}/decline/'
        response = self.client.patch(url)
        assert response.status_code == status.HTTP_200_OK

        # Verify request status is updated
        self.request.refresh_from_db()
        assert self.request.status == RequestState.DECLINED

    def test_decline_request_already_processed(self):
        # Authenticate as receiver
        self.client.force_authenticate(user=self.receiver)

        # Update request status to DECLINED
        self.request.status = RequestState.DECLINED
        self.request.save()

        # Try to decline the already processed request
        url = f'/api/v1/requests/{self.request.pk}/decline/'
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
        assert self.request.status == RequestState.CANCELLED

    def test_cancel_request_by_non_sender(self):
        # Authenticate as receiver
        self.client.force_authenticate(user=self.receiver)

        # Try to cancel request as receiver
        url = f'/api/v1/requests/{self.request.pk}/cancelled/'
        response = self.client.patch(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

        # Verify request status remains unchanged
        self.request.refresh_from_db()
        assert self.request.status == RequestState.PENDING

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
            visibility=Visibility.VISIBLE
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
        assert request_obj.status == RequestState.PENDING

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
            status=RequestState.PENDING)

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
            visibility=Visibility.VISIBLE
        )
        # Create  hidden company 
        self.company2 = Company.objects.create(
            name="TestCompany", 
            description="Test description", 
            owner=self.owner,
            visibility=Visibility.HIDDEN
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

        # Check permission denied
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

        # Check permission denied
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        