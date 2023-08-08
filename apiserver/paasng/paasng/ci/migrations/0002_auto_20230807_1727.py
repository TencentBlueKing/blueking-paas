# Generated by Django 3.2.12 on 2023-08-07 09:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ci', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ciatomjob',
            name='backend',
            field=models.CharField(choices=[('codecc', 'CodeCC')], max_length=32, verbose_name='CI引擎'),
        ),
        migrations.AlterField(
            model_name='ciatomjob',
            name='status',
            field=models.CharField(choices=[('successful', '成功'), ('failed', '失败'), ('pending', '等待'), ('interrupted', '已中断')], default='pending', max_length=16, verbose_name='执行状态'),
        ),
        migrations.AlterField(
            model_name='ciresourceappenvrelation',
            name='backend',
            field=models.CharField(choices=[('codecc', 'CodeCC')], max_length=32, verbose_name='CI引擎'),
        ),
        migrations.AlterField(
            model_name='ciresourceatom',
            name='backend',
            field=models.CharField(choices=[('codecc', 'CodeCC')], max_length=32, verbose_name='CI引擎'),
        ),
    ]
