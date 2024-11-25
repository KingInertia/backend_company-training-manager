from enum import Enum


class RequestState(Enum):
    AWAITING_RESPONSE = 'awaiting_response'
    ACCEPTED = 'accepted'
    DECLINED = 'declined'
    CANCELLED = 'cancelled'

    @classmethod
    def choices(cls):
        return [(state.value, state.name) for state in cls]
    
class Role(Enum):
    OWNER = 'owner'
    ADMIN = 'admin'
    MEMBER = 'member'

    @classmethod
    def choices(cls):
        return [(role.value, role.name) for role in cls]