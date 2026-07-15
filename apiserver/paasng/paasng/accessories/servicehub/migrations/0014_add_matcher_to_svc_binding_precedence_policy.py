# Generated manually for adding matcher field on 2025-07-15

from django.db import migrations, models


def populate_matcher_from_cond_fields(apps, schema_editor):
    """将存量 cond_type + cond_data 数据迁移到 matcher 字段"""
    ServiceBindingPrecedencePolicy = apps.get_model("servicehub", "ServiceBindingPrecedencePolicy")
    for policy in ServiceBindingPrecedencePolicy.objects.all():
        if not policy.cond_type or policy.cond_type == "always_match" or not policy.cond_data:
            policy.matcher = {}
        else:
            # cond_data 形如 {"region_in": ["xxx"]} / {"cluster_in": ["xxx"]} / {"usage_in": ["xxx"]}
            policy.matcher = {policy.cond_type: list(policy.cond_data.values())[0]}
        policy.save(update_fields=["matcher"])

class Migration(migrations.Migration):

    dependencies = [
        ("servicehub", "0013_serviceallocationpolicy"),
    ]

    operations = [
        migrations.AddField(
            model_name="servicebindingprecedencepolicy",
            name="matcher",
            field=models.JSONField(default=dict, verbose_name="匹配器"),
        ),
        migrations.RunPython(
            code=populate_matcher_from_cond_fields,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
