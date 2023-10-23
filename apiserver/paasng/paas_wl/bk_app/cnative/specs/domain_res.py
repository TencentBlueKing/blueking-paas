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

from paas_wl.bk_app.cnative.specs.crd import bk_app
from paas_wl.bk_app.cnative.specs.crd.bk_app import BkAppResource
from paas_wl.bk_app.cnative.specs.models.network_config import DomainResolution
from paasng.platform.applications.models import ModuleEnvironment

logger = logging.getLogger(__name__)


def inject_to_app_resource(env: ModuleEnvironment, app_resource: BkAppResource):
    """将 DomainResolution 配置注入到 BkAppResource 模型中"""
    if domain_res_queryset := DomainResolution.objects.filter(application_id=env.application.id):
        domain_res = domain_res_queryset.first()
        app_resource.spec.domainResolution = bk_app.DomainResolution(
            nameservers=domain_res.nameservers, hostAliases=domain_res.host_aliases
        )
