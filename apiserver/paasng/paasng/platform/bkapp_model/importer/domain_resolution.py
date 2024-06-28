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

from paas_wl.bk_app.cnative.specs.crd.bk_app import DomainResolution as DomainResolutionSpec
from paasng.platform.bkapp_model.models import DomainResolution
from paasng.platform.modules.models import Module

from .entities import CommonImportResult


def import_domain_resolution(module: Module, domain_res: DomainResolutionSpec) -> CommonImportResult:
    """Import domain resolution relations, existing data that is not in the input list may be removed.

    :param domain_res: DomainResolution Object
    :return: A result object.
    """
    ret = CommonImportResult()

    if not domain_res.nameservers and not domain_res.hostAliases:
        ret.deleted_num = DomainResolution.objects.filter(application=module.application).delete()
        return ret

    try:
        domain_config = DomainResolution.objects.get(application=module.application)
        nameservers = list(set(domain_config.nameservers) | set(domain_res.nameservers))
        host_aliases = list(set(domain_config.host_aliases) | set(domain_res.hostAliases))
    except DomainResolution.DoesNotExist:
        nameservers = domain_res.nameservers
        host_aliases = domain_res.hostAliases

    _, created = DomainResolution.objects.update_or_create(
        application=module.application,
        defaults={
            "nameservers": nameservers,
            "host_aliases": host_aliases,
        },
    )
    ret.incr_by_created_flag(created)

    return ret
