# Generated by Django 3.2.12 on 2024-04-07 05:44

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bkapp_model', '0010_auto_20231127_2039'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='moduleprocessspec',
            name='image',
        ),
        migrations.RemoveField(
            model_name='moduleprocessspec',
            name='image_credential_name',
        ),
        migrations.RemoveField(
            model_name='moduleprocessspec',
            name='image_pull_policy',
        ),
    ]
