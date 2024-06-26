# Generated by Django 3.2.12 on 2023-10-19 01:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('modules', '0010_remove_module_runtime_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='buildconfig',
            name='image',
            field=models.TextField(null=True, verbose_name='镜像地址'),
        ),
        migrations.AddField(
            model_name='buildconfig',
            name='image_credential_name',
            field=models.CharField(max_length=32, null=True, verbose_name='镜像凭证名称'),
        ),
        migrations.AddField(
            model_name='buildconfig',
            name='image_repository',
            field=models.TextField(null=True, verbose_name='镜像仓库'),
        ),
    ]
