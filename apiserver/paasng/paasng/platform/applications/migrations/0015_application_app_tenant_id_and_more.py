# Generated by Django 4.2.16 on 2024-12-21 06:38

from django.db import migrations, models
import paasng.core.tenant.constants


class Migration(migrations.Migration):

    dependencies = [
        ("applications", "0014_applicationdeploymentmoduleorder_user_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="application",
            name="app_tenant_id",
            field=models.CharField(
                default="default",
                help_text="应用对哪个租户的用户可用，当应用租户模式为全租户时，本字段值为空",
                max_length=32,
                verbose_name="应用租户 ID",
            ),
        ),
        migrations.AddField(
            model_name="application",
            name="app_tenant_mode",
            field=models.CharField(
                default=paasng.core.tenant.constants.AppTenantMode["GLOBAL"],
                help_text="应用在租户层面的可用范围，可选值：全租户、指定租户",
                max_length=16,
                verbose_name="应用租户模式",
            ),
        ),
        migrations.AddField(
            model_name="application",
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
