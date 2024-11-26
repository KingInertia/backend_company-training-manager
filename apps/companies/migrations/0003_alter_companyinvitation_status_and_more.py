# Generated by Django 5.1.2 on 2024-11-26 15:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('companies', '0002_companyinvitation_companyrequest_companymember'),
    ]

    operations = [
        migrations.AlterField(
            model_name='companyinvitation',
            name='status',
            field=models.CharField(choices=[('awaiting_response', 'Awaiting Response'), ('accepted', 'Accepted'), ('declined', 'Declined'), ('cancelled', 'Cancelled')], default='awaiting_response', max_length=20),
        ),
        migrations.AlterField(
            model_name='companymember',
            name='role',
            field=models.CharField(choices=[('owner', 'Owner'), ('member', 'Member')], default='member', max_length=10),
        ),
        migrations.AlterField(
            model_name='companyrequest',
            name='status',
            field=models.CharField(choices=[('awaiting_response', 'Awaiting Response'), ('accepted', 'Accepted'), ('declined', 'Declined'), ('cancelled', 'Cancelled')], default='awaiting_response', max_length=20),
        ),
    ]
