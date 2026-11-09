import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0005_remove_project_name_at_deletion_alter_project_name_and_more'),
        ('publication', '0001_initial'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='DevCenterAppBinding',
            new_name='BkPaaSAppBinding',
        ),
        migrations.AlterField(
            model_name='bkpaasappbinding',
            name='project',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='bkpaas_app_binding', to='projects.project', verbose_name='所属项目'),
        ),
        migrations.AlterField(
            model_name='bkpaasappbinding',
            name='tenant_id',
            field=models.CharField(db_index=True, default='default', help_text='本条数据的所属租户', max_length=32, verbose_name='租户 ID'),
        ),
        migrations.AlterField(
            model_name='publicationtask',
            name='tenant_id',
            field=models.CharField(db_index=True, default='default', help_text='本条数据的所属租户', max_length=32, verbose_name='租户 ID'),
        ),
        migrations.RemoveField(
            model_name='publicationtask',
            name='last_polled_at',
        ),
        migrations.RemoveField(
            model_name='publicationtask',
            name='access_url_polls',
        ),
    ]
