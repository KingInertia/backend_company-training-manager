from rest_framework import serializers

from .models import Company


class CompanySerializer(serializers.ModelSerializer):
    owner = serializers.PrimaryKeyRelatedField(read_only=True)
    class Meta:
        model = Company
        fields = ('__all__')

class CompanyListSerializer (serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ('__all__')