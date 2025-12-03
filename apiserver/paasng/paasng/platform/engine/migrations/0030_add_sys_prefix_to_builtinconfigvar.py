"""
Add BKPAAS_ prefix to all existing BuiltinConfigVar.key values.

This is a data migration: at the time of this migration, all existing BuiltinConfigVar
records were created without any prefix in the `key` field, but the actual environment
variable name used by applications has BKPAAS_ prefix added by the code.

For example, if key="VAR", the actual env var is "BKPAAS_VAR".
If key="BKPAAS_VAR", the actual env var is "BKPAAS_BKPAAS_VAR".

This migration updates all keys to include the BKPAAS_ prefix to match the actual
environment variable names used by applications.
"""

from django.db import migrations

from django.conf import settings


def add_sys_prefix(apps, schema_editor):
    BuiltinConfigVar = apps.get_model("engine", "BuiltinConfigVar")

    for obj in BuiltinConfigVar.objects.all():
        new_key = settings.CONFIGVAR_SYSTEM_PREFIX + obj.key
        # Avoid unique constraint violation: if target exists, skip
        if BuiltinConfigVar.objects.filter(key=new_key).exists():
            # Use print so migration output shows in logs
            print(f"[migration] skip BuiltinConfigVar id={obj.pk} key={obj.key}: {new_key} already exists")
            continue

        obj.key = new_key
        obj.save(update_fields=["key"])


class Migration(migrations.Migration):
    dependencies = [("engine", "0029_moduleenvironmentoperations_tenant_id")]

    operations = [migrations.RunPython(add_sys_prefix)]
