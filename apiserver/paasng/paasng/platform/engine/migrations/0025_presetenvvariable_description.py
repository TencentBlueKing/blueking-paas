# Generated by Django 4.2.17 on 2025-04-15 07:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('engine', '0024_configvar_tenant_id_deployment_tenant_id_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='presetenvvariable',
            name='description',
            field=models.CharField(blank=True, max_length=200, null=True, verbose_name='变量描述'),
        ),
    ]
