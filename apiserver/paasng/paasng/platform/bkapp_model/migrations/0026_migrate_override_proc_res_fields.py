# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
# Licensed under the MIT License (the "License"); you may not use this file except
# in compliance with the License. You may obtain a copy of the License at
#
#     http://opensource.org/licenses/MIT
#
# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the License for the specific language governing permissions and
# limitations under the License.
#
# We undertake not to change the open source license (MIT license) applicable
# to the current version of the project delivered to anyone in the future.

from django.db import migrations, models

def migrate_override_fields_data(apps, schema_editor):
    """Migrate data from old fields to new fields in ProcessSpecEnvOverlay model."""
    ProcessSpecEnvOverlay = apps.get_model('bkapp_model', 'ProcessSpecEnvOverlay')

    for overlay in ProcessSpecEnvOverlay.objects.filter(override_proc_res__isnull=False):
        override_proc_res = overlay.override_proc_res

        if not override_proc_res:
            continue

        # Case 1: Using a predefined plan - {"plan": "default"}
        if 'plan' in override_proc_res:
            overlay.override_plan_name = override_proc_res['plan']
            overlay.override_resources = None
        # Case 2: Custom resources - {"limits": {...}, "requests": {...}}
        else:
            overlay.override_plan_name = None
            overlay.override_resources = override_proc_res

        overlay.save(update_fields=['override_plan_name', 'override_resources'])


class Migration(migrations.Migration):

    dependencies = [
        ('bkapp_model', '0025_processspecenvoverlay_override_plan_name_and_more'),
    ]

    operations = [
        # Migrate data from old fields to new fields
        migrations.RunPython(migrate_override_fields_data),
        # Delete the deprecated field
        migrations.RemoveField(
            model_name='processspecenvoverlay',
            name='override_proc_res',
        ),
    ]
