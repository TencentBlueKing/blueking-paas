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

from paasng.platform.bkapp_model.entities import DomainResolution
from paasng.platform.bkapp_model.models import DomainResolution as DomainResolutionDB
from paasng.platform.modules.models import Module

from .result import CommonSyncResult


def sync_domain_resolution(module: Module, domain_res: DomainResolution) -> CommonSyncResult:
    """Sync domain resolution relations to db model, existing data that is not in the input list may be removed.

    :param module: app module
    :param domain_res: DomainResolution entity
    :return: sync result
    """

    ret = CommonSyncResult()

    if not domain_res.nameservers and not domain_res.host_aliases:
        ret.deleted_num, _ = DomainResolutionDB.objects.filter(application=module.application).delete()
        return ret

    try:
        domain_config = DomainResolutionDB.objects.get(application=module.application)
        # INFO/FIXME: 此处取并集，会导致条目数在修改并重复同步后，总是增多，不会减少？
        nameservers = list(set(domain_config.nameservers) | set(domain_res.nameservers))
        host_aliases = list(set(domain_config.host_aliases) | set(domain_res.host_aliases))
    except DomainResolutionDB.DoesNotExist:
        nameservers = domain_res.nameservers
        host_aliases = domain_res.host_aliases

    _, created = DomainResolutionDB.objects.update_or_create(
        application=module.application,
        defaults={
            "nameservers": nameservers,
            "host_aliases": host_aliases,
        },
    )
    ret.incr_by_created_flag(created)

    return ret
