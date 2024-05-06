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
from paas_wl.bk_app.cnative.specs.crd.bk_app import SvcDiscConfig as SvcDiscConfigSpec
from paasng.platform.bkapp_model.models import SvcDiscConfig
from paasng.platform.modules.models import Module

from .entities import CommonImportResult


def import_svc_discovery(module: Module, svc_disc: SvcDiscConfigSpec) -> CommonImportResult:
    """Import svc discovery relations, existing data that is not in the input list may be removed.

    :param svc_disc: SvcDiscConfig Object
    :return: A result object.
    """
    ret = CommonImportResult()

    try:
        svc_config = SvcDiscConfig.objects.get(application=module.application)
    except SvcDiscConfig.DoesNotExist:
        svc_config = None

    if not svc_disc.bkSaaS:
        if svc_config:
            svc_config.delete()
            ret.deleted_num += 1
        return ret

    if svc_config:
        updated_bk_saas = list(set(svc_config.bk_saas) | set(svc_disc.bkSaaS))
        if updated_bk_saas != svc_config.bk_saas:
            svc_config.bk_saas = updated_bk_saas
            svc_config.save(update_fields=["bk_saas"])
            ret.updated_num += 1
    else:
        SvcDiscConfig.objects.create(application=module.application, bk_saas=svc_disc.bkSaaS)
        ret.created_num += 1

    return ret
