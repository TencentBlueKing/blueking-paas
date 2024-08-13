# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
# Licensed under the MIT License (the "License"); you may not use this file except
# in compliance with the License. You may obtain a copy of the License at
#
#     http://opensource.org/licenses/MIT
#
# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the License for the specific language governing permissions and
# limitations under the License.
#
# We undertake not to change the open source license (MIT license) applicable
# to the current version of the project delivered to anyone in the future.

from paasng.platform.bkapp_model.entities import SvcDiscConfig
from paasng.platform.bkapp_model.models import SvcDiscConfig as SvcDiscConfigDB
from paasng.platform.modules.models import Module

from .result import CommonSyncResult


def sync_svc_discovery(module: Module, svc_disc: SvcDiscConfig) -> CommonSyncResult:
    """Sync svc discovery relations to db model, existing data that is not in the input list may be removed.

    :param module: app module
    :param svc_disc: SvcDiscConfig Object
    :return: sync result
    """
    ret = CommonSyncResult()

    if not svc_disc.bk_saas:
        ret.deleted_num, _ = SvcDiscConfigDB.objects.filter(application=module.application).delete()
        return ret

    try:
        svc_config = SvcDiscConfigDB.objects.get(application=module.application)
        bk_saas = list(set(svc_config.bk_saas) | set(svc_disc.bk_saas))
    except SvcDiscConfigDB.DoesNotExist:
        bk_saas = svc_disc.bk_saas

    _, created = SvcDiscConfigDB.objects.update_or_create(
        application=module.application,
        defaults={"bk_saas": bk_saas},
    )
    ret.incr_by_created_flag(created)

    return ret
