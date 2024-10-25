# Generated by Django 3.2.25 on 2024-10-25 03:56

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('applications', '0012_application_is_ai_agent_app'),
        ('monitor', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='AppDashBoard',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(help_text='仪表盘名称，如：bksaas/framework-python', max_length=64, unique=True)),
                ('display_name', models.CharField(help_text='仪表盘展示名称，如：Python 开发框架内置仪表盘', max_length=512)),
                ('template_version', models.CharField(help_text='模板版本更新时，可以根据该字段作为批量刷新仪表盘', max_length=32)),
                ('language', models.CharField(max_length=32, verbose_name='仪表盘所属语言')),
                ('application', models.ForeignKey(db_constraint=False, on_delete=django.db.models.deletion.CASCADE, related_name='dashboards', to='applications.application')),
            ],
            options={
                'unique_together': {('application', 'name')},
            },
        ),
    ]
