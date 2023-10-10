# -*- coding: utf-8 -*-
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
from pathlib import Path

import jinja2
from django.apps import AppConfig
from django.conf import settings

IAM_CONTEXT = {
    'IAM_PAAS_V3_SYSTEM_ID': settings.IAM_PAAS_V3_SYSTEM_ID,
    'APP_CODE': settings.BK_APP_CODE,
}


def render_migrate_json():
    """根据模板生成最终的 migrate json 文件"""
    iam_tpl_path = Path(settings.BASE_DIR) / 'support-files' / 'iam_tpl'
    iam_tpl = Path(settings.BASE_DIR) / 'support-files' / 'iam'
    iam_tpl.mkdir(exist_ok=True)

    j2_env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(iam_tpl_path)), trim_blocks=True)
    for dir in iam_tpl_path.iterdir():
        j2_env.get_template(dir.name).stream(**IAM_CONTEXT).dump(str(iam_tpl / dir.name[:-3]))


class BKPaaSIAMMigrationConfig(AppConfig):
    name = 'paasng.infras.iam.bkpaas_iam_migration'
    label = 'bkpaas_iam_migration'

    def ready(self):
        render_migrate_json()
