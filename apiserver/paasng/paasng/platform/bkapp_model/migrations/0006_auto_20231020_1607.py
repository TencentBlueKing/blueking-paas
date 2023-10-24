"""
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except
in compliance with the License. You may obtain a copy of the License at

    http://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software distributed under
the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the specific language governing permissions and
limitations under the License.

We undertake not to change the open source license (MIT license) applicable
to the current version of the project delivered to anyone in the future.
"""
# Generated by Django 3.2.12 on 2023-10-20 08:07

from django.db import migrations
from paasng.platform.modules.constants import DeployHookType


def forwards(apps, schema_editor):
    """Migrate all DeployConfig.hooks to ModuleDeployHook"""
    DeployConfig = apps.get_model('modules', 'DeployConfig')
    ModuleDeployHook = apps.get_model('bkapp_model', 'ModuleDeployHook')

    for cfg in DeployConfig.objects.exclude(hooks=[]):
        module = cfg.module
        hook = cfg.hooks.get_hook(DeployHookType.PRE_RELEASE_HOOK)
        if not hook:
            continue
        ModuleDeployHook.objects.update_or_create(
            module=module,
            type=DeployHookType.PRE_RELEASE_HOOK,
            defaults={
                "proc_command": hook.command,
                "enabled": hook.enabled,
            }
        )


class Migration(migrations.Migration):

    dependencies = [
        ('bkapp_model', '0005_moduledeployhook'),
    ]

    operations = [
        migrations.RunPython(code=forwards)
    ]
