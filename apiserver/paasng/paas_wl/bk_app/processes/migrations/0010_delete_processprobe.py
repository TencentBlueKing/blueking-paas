# Generated by Django 4.2.16 on 2025-02-28 12:02

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('processes', '0009_processspec_tenant_id'),
    ]

    operations = [
        migrations.DeleteModel(
            name='ProcessProbe',
        ),
    ]
