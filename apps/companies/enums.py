from django.db import models
from django.utils.translation import gettext_lazy as _


class RequestState(models.TextChoices):
    PENDING = 'pending', 'Awaiting Response'
    ACCEPTED = 'accepted', 'Accepted'
    DECLINED = 'declined', 'Declined'
    CANCELLED = 'cancelled', 'Cancelled'

    
class Role(models.TextChoices):
    OWNER = 'owner', _('Owner')
    MEMBER = 'member', _('Member')
    
class Visibility(models.TextChoices):
        HIDDEN = 'hidden', _('Hidden')
        VISIBLE = 'visible', _('Visible')
