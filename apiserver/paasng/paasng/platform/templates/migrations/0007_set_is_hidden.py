# Generated by Django 4.2.17 on 2025-03-18 07:20

from django.db import migrations

def forwards_func(apps, schema_editor):
    """Set the initial value of is_hidden field for all Template objects."""
    Template = apps.get_model("templates", "Template")
    for t in Template.objects.all():
        if not t.enabled_regions:
            t.is_hidden = True
            t.save(update_fields=["is_hidden"])


class Migration(migrations.Migration):

    dependencies = [
        ("templates", "0006_template_is_hidden"),
    ]

    operations = [migrations.RunPython(forwards_func)]
