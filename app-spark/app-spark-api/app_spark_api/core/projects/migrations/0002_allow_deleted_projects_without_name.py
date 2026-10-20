from django.db import migrations, models


def release_names_of_deleted_projects(apps, schema_editor):
    """Give soft-deleted rows written before this migration the same shape deletion now leaves."""
    Project = apps.get_model("projects", "Project")

    # 旧软删除行若仍占着名称，同名新建会撞上唯一约束。
    deleted = Project.objects.filter(is_deleted=True, name__isnull=False)
    deleted.update(name_at_deletion=models.F("name"))
    deleted.update(name=None)


class Migration(migrations.Migration):
    dependencies = [
        ("projects", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="project",
            name="name",
            field=models.CharField(max_length=20, null=True, verbose_name="项目名称"),
        ),
        migrations.AddField(
            model_name="project",
            name="name_at_deletion",
            field=models.CharField(blank=True, default="", max_length=20, verbose_name="删除前的项目名称"),
        ),
        migrations.RunPython(release_names_of_deleted_projects, migrations.RunPython.noop),
    ]
