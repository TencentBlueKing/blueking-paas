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
from paasng.platform.bkapp_model import fieldmgr
from paasng.platform.bkapp_model.entities import SvcDiscConfig
from paasng.platform.bkapp_model.models import SvcDiscConfig as SvcDiscConfigDB
from paasng.platform.modules.models import Module
from paasng.utils.structure import NOTSET, NotSetType

from .result import CommonSyncResult


def sync_svc_discovery(
    module: Module,
    svc_disc: SvcDiscConfig | NotSetType | None,
    manager: fieldmgr.FieldMgrName,
) -> CommonSyncResult:
    """Sync svc discovery relations to db model, existing data that is not in the input list may be removed.

    :param module: The app module.
    :param svc_disc: SvcDiscConfig Object.
    :param manger: The manager performing this action.
    :return: Sync result
    """
    ret = CommonSyncResult()

    # If the field is not managed by current manager and the value is not set, do nothing.
    # **Always switch to the default module for querying field manager, because the
    # svc_discovery field is on the application level.**
    default_module = module.application.get_default_module()
    field_mgr = fieldmgr.FieldManager(
        default_module, fieldmgr.F_SVC_DISCOVERY, default_if_unmanaged=fieldmgr.FieldMgrName.WEB_FORM
    )
    if not field_mgr.is_managed_by(manager) and svc_disc == NOTSET:
        return ret

    # Always force rewrite the value and set the field manager
    if isinstance(svc_disc, NotSetType):
        field_mgr.reset()
        ret.deleted_num, _ = SvcDiscConfigDB.objects.filter(application=module.application).delete()
        return ret
    if svc_disc is None or not svc_disc.bk_saas:
        ret.deleted_num, _ = SvcDiscConfigDB.objects.filter(application=module.application).delete()
        return ret

    _, created = SvcDiscConfigDB.objects.update_or_create(
        application=module.application,
        defaults={"bk_saas": svc_disc.bk_saas},
    )
    ret.incr_by_created_flag(created)
    field_mgr.set(manager)
    return ret
