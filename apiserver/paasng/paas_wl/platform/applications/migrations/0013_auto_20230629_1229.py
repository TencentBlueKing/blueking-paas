# Generated by Django 3.2.12 on 2023-06-29 04:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0012_auto_20230620_1302'),
    ]

    operations = [
        migrations.AddField(
            model_name='buildprocess',
            name='completed_at',
            field=models.DateTimeField(help_text='failed/successful/interrupted 都是完成', null=True, verbose_name='完成时间'),
        ),
        migrations.AddField(
            model_name='buildprocess',
            name='generation',
            field=models.PositiveBigIntegerField(default=0, help_text='每个应用独立的自增ID', verbose_name='自增ID'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='buildprocess',
            name='invoke_message',
            field=models.CharField(blank=True, help_text='触发信息', max_length=255, null=True),
        ),
    ]
