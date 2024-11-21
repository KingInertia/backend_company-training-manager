from django.contrib import admin

from .models import Company


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'visibility', 'created_at')
    search_fields = ('name', 'description')
    list_filter = ('owner', 'created_at', 'updated_at')
