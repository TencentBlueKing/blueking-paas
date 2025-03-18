# Generated by Django 4.2.17 on 2025-03-18 07:25
import logging

from django.db import migrations
from django.conf import settings

logger = logging.getLogger(__name__)

def forwards_func(apps, schema_editor):
    """Update the value of blob_url field for all Template objects, change it from dict
    to string type.
    
    WARNING: value might be discarded during this migration because the original dict
    might contain multiple regions' blob urls, but we only keep one.
    """
    Template = apps.get_model("templates", "Template")
    for t in Template.objects.all():
        # Modify the empty value
        if t.blob_url == {}:
            t.blob_url = ""
            t.save(update_fields=["blob_url"])
            continue

        if not (isinstance(t.blob_url, dict) and t.blob_url):
            continue

        # Use a random(the first) value as the default value
        the_first_value =  list(t.blob_url.values())[0]
        if len(t.blob_url) == 1:
            value = the_first_value
        else:
            value = t.blob_url.get(settings.DEFAULT_REGION_NAME, the_first_value)
            logger.warning(
                "Template %s has multiple blob urls, picked: %s, original: %s", t.name, value, t.blob_url
            )

        t.blob_url = value
        t.save(update_fields=["blob_url"])


class Migration(migrations.Migration):

    dependencies = [
        ("templates", "0008_remove_template_enabled_regions_and_more"),
    ]

    operations = [migrations.RunPython(forwards_func)]