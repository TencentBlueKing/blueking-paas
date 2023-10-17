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
from paas_wl.bk_app.cnative.specs.crd.bk_app import BkAppResource
from paas_wl.bk_app.cnative.specs.models import AppModelResource
from paas_wl.utils.error_codes import error_codes
from paasng.platform.applications.models import Application
from paasng.platform.modules.models import Module


def get_bkapp(application: Application, module: Module) -> BkAppResource:
    """shortcut for getting AppModelResource from db and parsed it to BkAppResource"""
    try:
        model_resource = AppModelResource.objects.get(application_id=application.id, module_id=module.id)
    except AppModelResource.DoesNotExist:
        raise error_codes.BKAPP_NOT_SET
    try:
        return BkAppResource(**model_resource.revision.json_value)
    except ValueError:
        raise error_codes.INVALID_MRES
