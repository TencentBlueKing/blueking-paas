from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("conversations", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="conversation",
            name="preview_origin",
            field=models.CharField(blank=True, default=None, max_length=512, null=True, verbose_name="预览地址"),
        ),
    ]
