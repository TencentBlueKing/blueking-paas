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
from paasng.platform.bkapp_model.entities import DomainResolution
from paasng.platform.bkapp_model.models import DomainResolution as DomainResolutionDB
from paasng.platform.modules.models import Module
from paasng.utils.structure import NOTSET, NotSetType

from .result import CommonSyncResult


def sync_domain_resolution(
    module: Module, domain_res: DomainResolution | NotSetType | None, manager: fieldmgr.FieldMgrName
) -> CommonSyncResult:
    """Sync domain resolution relations to db model, existing data that is not in the input list may be removed.

    :param module: app module
    :param domain_res: DomainResolution entity
    :param manager: The manager performing this action
    :return: sync result
    """

    ret = CommonSyncResult()

    # If the field is not managed by current manager and the value is not set, do nothing.
    # **Always switch to the default module for querying field manager, because the
    # domain_resolution field is on the application level.**
    default_module = module.application.get_default_module()
    field_mgr = fieldmgr.FieldManager(default_module, fieldmgr.F_DOMAIN_RESOLUTION)
    if not field_mgr.is_managed_by(manager) and domain_res == NOTSET:
        return ret

    # Remove the db obj if the value is not set or empty
    if isinstance(domain_res, NotSetType):
        # Reset the field manager when the data is not set
        field_mgr.reset()
        ret.deleted_num, _ = DomainResolutionDB.objects.filter(application=module.application).delete()
        return ret
    if domain_res is None or not (domain_res.nameservers or domain_res.host_aliases):
        ret.deleted_num, _ = DomainResolutionDB.objects.filter(application=module.application).delete()
        return ret

    _, created = DomainResolutionDB.objects.update_or_create(
        application=module.application,
        defaults={
            "nameservers": domain_res.nameservers,
            "host_aliases": domain_res.host_aliases,
        },
    )
    ret.incr_by_created_flag(created)
    field_mgr.set(manager)
    return ret
