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
from typing import Optional

from paasng.platform.applications.models import ModuleEnvironment
from paasng.platform.region.models import get_region


def to_dns_safe(s: str) -> str:
    """Transform some string to dns safe"""
    return s.replace('_', '--').lower()


def get_legacy_url(env: ModuleEnvironment) -> Optional[str]:
    """Deprecated: Get legacy URL address which is a hard-coded value generated
    y region configuration.

    :return: None if not configured.
    """
    app = env.application
    if tmpl := get_region(app.region).basic_info.link_engine_app:
        return tmpl.format(code=app.code, region=app.region, name=env.engine_app.name)
    return None
