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
import logging

from django.db import migrations

logger = logging.getLogger(__name__)


def migrate_spec_cls(apps, schema_editor):
    """Migrate the "spec_cls" attribute to new import locations.
    
    The project structure has been updated in 2023/10, we need to update the import
    locations of each config object in order to make the import work. 
    """
    old_loc = 'paasng.dev_resources.sourcectl'
    new_loc = 'paasng.platform.sourcectl'

    SourceTypeSpecConfig = apps.get_model('sourcectl', 'SourceTypeSpecConfig')
    for c in SourceTypeSpecConfig.objects.all():
        if c.spec_cls.startswith(old_loc):
            c.spec_cls = new_loc + c.spec_cls[len(old_loc):]
            c.save(update_fields=['spec_cls'])


class Migration(migrations.Migration):
    dependencies = [
        ('sourcectl', '0010_alter_sourcetypespecconfig_client_secret'),
    ]

    operations = [
        migrations.RunPython(migrate_spec_cls),
    ]