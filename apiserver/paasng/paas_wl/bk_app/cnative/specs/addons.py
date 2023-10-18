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
import json

from paas_wl.bk_app.cnative.specs.constants import BKPAAS_ADDONS_ANNO_KEY, ApiVersion
from paas_wl.bk_app.cnative.specs.crd import bk_app
from paasng.accessories.servicehub.manager import mixed_service_mgr
from paasng.platform.applications.models import ModuleEnvironment


def inject_to_app_resource(env: ModuleEnvironment, bkapp_res: bk_app.BkAppResource):
    """将 增强服务(addon) 配置注入到 BkAppResource 模型中"""
    # inject addons services to annotations for legacy version manifest
    bound_addon_names = [svc.name for svc in mixed_service_mgr.list_binded(env.module)]
    bkapp_res.metadata.annotations[BKPAAS_ADDONS_ANNO_KEY] = json.dumps(bound_addon_names)

    if bkapp_res.apiVersion == ApiVersion.V1ALPHA2:
        # inject addons services to specs
        predefined_addons_names = {svc.name for svc in bkapp_res.spec.addons}
        for svc_name in bound_addon_names:
            if svc_name not in predefined_addons_names:
                bkapp_res.spec.addons.append(bk_app.BkAppAddon(name=svc_name))
