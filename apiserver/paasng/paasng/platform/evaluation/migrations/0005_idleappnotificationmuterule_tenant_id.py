# Generated by Django 4.2.17 on 2025-01-10 09:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("evaluation", "0004_idleappnotificationmuterule"),
    ]

    operations = [
        migrations.AddField(
            model_name="idleappnotificationmuterule",
            name="tenant_id",
            field=models.CharField(
                db_index=True,
                default="default",
                help_text="本条数据的所属租户",
                max_length=32,
                verbose_name="租户 ID",
            ),
        ),
    ]
