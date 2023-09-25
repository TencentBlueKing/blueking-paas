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

from paas_wl.cnative.specs.constants import BKPAAS_ADDONS_ANNO_KEY, ApiVersion
from paas_wl.cnative.specs.crd import bk_app
from paasng.dev_resources.servicehub.manager import mixed_service_mgr
from paasng.platform.applications.models import ModuleEnvironment


def inject_to_app_resource(env: ModuleEnvironment, app_resource: bk_app.BkAppResource):
    """将 增强服务(addon) 配置注入到 BkAppResource 模型中"""
    # inject addons services to annotations for legacy version manifest
    bound_addon_names = [svc.name for svc in mixed_service_mgr.list_binded(env.module)]
    app_resource.metadata.annotations[BKPAAS_ADDONS_ANNO_KEY] = json.dumps(bound_addon_names)

    if app_resource.apiVersion == ApiVersion.V1ALPHA2:
        # inject addons services to specs
        predefined_addons = app_resource.spec.addons
        addons = [
            bk_app.BkAppAddon(
                name=name,
            )
            for name in bound_addon_names
        ]

        if predefined_addons and ({svc.name for svc in predefined_addons} - set(bound_addon_names)):
            # manifest 中声明的增强服务列表与在 v3 上启用的列表不一致, 可能是通过 cli 触发部署且需要打开增强服务
            # 目前的策略是合并 addons 列表
            # TODO: 讨论是否需要兼容 cli 更新的情况
            for svc in predefined_addons:
                if svc.name in bound_addon_names:
                    continue
                addons.append(svc)
        app_resource.spec.addons = addons
