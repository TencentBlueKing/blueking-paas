# Generated manually for adding matcher field on 2025-07-15

import logging

from django.db import migrations, models

logger = logging.getLogger(__name__)

# 旧版 ServiceBindingPrecedencePolicy.cond_data 是一个 dict[str, list[str]],
# 其 key 与 cond_type 没有显式的映射关系, 需要按 cond_type 显式读取对应的 key,
LEGACY_COND_DATA_KEYS: dict[str, str] = {
    "region_in": "regions",
    "cluster_in": "cluster_names",
    "usage_in": "usages",
}


def populate_matcher_from_cond_fields(apps, schema_editor):
    """将 cond_type + cond_data 迁移为 matcher.

    转换规则 (按 cond_type 显式映射到旧 cond_data 的 key):
    - cond_type == "region_in"  -> matcher = {"region_in": cond_data["regions"]}
    - cond_type == "cluster_in" -> matcher = {"cluster_in": cond_data["cluster_names"]}
    - cond_type == "usage_in"   -> matcher = {"usage_in": cond_data["usages"]}
    - cond_type == "always_match" -> matcher = {}

    异常数据 (cond_type 非空但 cond_data 为空, 或按上述映射找不到 key) 打印告警并跳过.
    """
    ServiceBindingPrecedencePolicy = apps.get_model("servicehub", "ServiceBindingPrecedencePolicy")
    for policy in ServiceBindingPrecedencePolicy.objects.all():
        cond_type = policy.cond_type
        cond_data = policy.cond_data

        if cond_type == "always_match":
            policy.matcher = {}
        elif not cond_data:
            # 非 always_match 但 cond_data 为空, 不迁移记录并跳过
            logger.warning(
                "ServiceBindingPrecedencePolicy(id=%s) has non-always_match cond_type=%r but empty cond_data, "
                "skip migrating this record.",
                policy.pk,
                cond_type,
            )
            continue
        else:
            legacy_key = LEGACY_COND_DATA_KEYS.get(cond_type)
            values = cond_data.get(legacy_key) if legacy_key else None
            if values is None:
                # 异常结构, 记录后跳过
                logger.warning(
                    "ServiceBindingPrecedencePolicy(id=%s) has unexpected cond_type=%r with cond_data=%r; "
                    "expected key %r not found, skip migrating this record.",
                    policy.pk,
                    cond_type,
                    dict(cond_data),
                    legacy_key,
                )
                continue
            policy.matcher = {cond_type: values}
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
