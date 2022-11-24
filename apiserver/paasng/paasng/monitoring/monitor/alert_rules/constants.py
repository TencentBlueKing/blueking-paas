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
from django.utils.translation import gettext_lazy as _

from paasng.platform.applications.constants import AppEnvironment

RUN_ENVS = [AppEnvironment.STAGING.value, AppEnvironment.PRODUCTION.value]

DEFAULT_RULE_CONFIGS = {
    'module_scoped': {
        'high_cpu_usage': {
            'display_name': _('CPU 使用率过高'),
            'threshold_expr': '>= 0.8',  # 使用率 80%
        },
        'high_mem_usage': {
            'display_name': _('内存使用率过高'),
            'threshold_expr': '>= 0.95',  # 使用率 95%
        },
    },
    'app_scoped': {
        'page_50x': {
            'display_name': _('应用首页访问异常'),
            'threshold_expr': '>= 500',
        }
    },
}
