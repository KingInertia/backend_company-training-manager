from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from tools.models import TimeStampedModel

from .enums import RequestState, Role


class Company(TimeStampedModel):
    VISIBILITY_CHOICES = [
        ('hidden', 'hidden'),
        ('visible', 'visible'),
    ]
    name = models.CharField(max_length=50)
    description = models.TextField()
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='companies',
        on_delete=models.CASCADE)
    visibility = models.CharField(
        max_length=7,
        choices=VISIBILITY_CHOICES,
        default='visible'
    
    )
    class Meta:
        verbose_name_plural = "Companies"
        

class CompanyInvitation(TimeStampedModel):
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='sent_invitations',
        on_delete=models.CASCADE
    
    )
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    receiver= models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='received_invitations',
        on_delete=models.CASCADE
    
    )
    status = models.CharField(
        max_length=20,
        choices=RequestState.choices(),
        default=RequestState.AWAITING_RESPONSE.value,
        
    )
    
    def __str__(self):
        return f"Invitation from {self.sender} to {self.receiver} for {self.company}"
    
    def clean(self):
        if self.sender == self.receiver:
            raise ValidationError("Sender and receiver cannot be the same user.")    

    def save(self, *args, **kwargs):
            self.clean()
            super().save(*args, **kwargs)
    
    
class CompanyRequest(TimeStampedModel):
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='sent_requests',
        on_delete=models.CASCADE
    
    )
    receiver= models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='received_requests',
        on_delete=models.CASCADE
    
    )
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    status = models.CharField(
        max_length=20,
        choices=RequestState.choices(),
        default=RequestState.AWAITING_RESPONSE.value,
        
    )
    
    def __str__(self):
        return f"Request from {self.sender} to join {self.company}"


class CompanyMember(TimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='company_memberships'
    )
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='memberships'
    )
    role = models.CharField(
        max_length=10,
        choices=Role.choices(),
        default=Role.MEMBER.value
    )

    class Meta:
        unique_together = ('user', 'company') 

    def __str__(self):
        return f"{self.user} - {self.company} ({self.role})"    