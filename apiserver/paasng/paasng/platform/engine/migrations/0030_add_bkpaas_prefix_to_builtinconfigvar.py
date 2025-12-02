"""
Add BKPAAS_ prefix to existing BuiltinConfigVar.key values when missing.

This is a data migration: for every BuiltinConfigVar instance whose `key` does not
start with one of the allowed prefixes (BK_, BKAPP_, BKPAAS_), we will update it to
have the BKPAAS_ prefix. If the target key already exists, the row will be skipped
to avoid unique constraint violations and a message will be printed.

Reversible: the reverse operation will remove the BKPAAS_ prefix from keys that
start with BKPAAS_, skipping any row that would conflict with an existing key.
"""

from django.db import migrations

from paasng.plat_mgt.config_vars.constants import CustomBuiltinConfigVarPrefix


def add_bkpaas_prefix(apps, schema_editor):
    BuiltinConfigVar = apps.get_model("engine", "BuiltinConfigVar")
    allowed_prefixes = CustomBuiltinConfigVarPrefix.get_values()

    for obj in BuiltinConfigVar.objects.all():
        key = obj.key

        if any(key.startswith(p) for p in allowed_prefixes):
            # already has one of allowed prefixes
            continue

        new_key = "BKPAAS_" + key
        # Avoid unique constraint violation: if target exists, skip
        if BuiltinConfigVar.objects.filter(key=new_key).exists():
            # Use print so migration output shows in logs
            print(f"[migration] skip BuiltinConfigVar id={obj.pk} key={key}: {new_key} already exists")
            continue

        obj.key = new_key
        obj.save(update_fields=["key"])


def remove_bkpaas_prefix(apps, schema_editor):
    BuiltinConfigVar = apps.get_model("engine", "BuiltinConfigVar")
    prefix = "BKPAAS_"

    for obj in BuiltinConfigVar.objects.filter(key__startswith=prefix):
        unprefixed = obj.key[len(prefix) :]
        # Avoid unique constraint violation when reverting
        if BuiltinConfigVar.objects.filter(key=unprefixed).exists():
            print(f"[migration] skip revert BuiltinConfigVar id={obj.pk} key={obj.key}: {unprefixed} exists")
            continue

        obj.key = unprefixed
        obj.save(update_fields=["key"])


class Migration(migrations.Migration):
    dependencies = [("engine", "0029_moduleenvironmentoperations_tenant_id")]

    operations = [migrations.RunPython(add_bkpaas_prefix, remove_bkpaas_prefix)]
