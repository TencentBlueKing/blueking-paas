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
from paas_wl.bk_app.cnative.specs.crd.bk_app import DomainResolution as DomainResolutionSpec
from paasng.platform.bkapp_model.models import DomainResolution
from paasng.platform.modules.models import Module

from .entities import CommonImportResult


def import_domain_resolution(module: Module, domain_res: DomainResolutionSpec) -> CommonImportResult:
    """Import domain resolution relations, existing data that is not in the input list may be removed.

    :param domin_res: DomainResolution Object
    :return: A result object.
    """
    ret = CommonImportResult()

    try:
        domain_config = DomainResolution.objects.get(application=module.application)
    except DomainResolution.DoesNotExist:
        domain_config = None

    if domain_config and not domain_res.nameservers and not domain_res.hostAliases:
        domain_config.delete()
        ret.deleted_num += 1
        return ret

    if domain_config:
        updated_nameservers = list(set(domain_config.nameservers) | set(domain_res.nameservers))
        if updated_nameservers != domain_config.nameservers:
            domain_config.nameservers = updated_nameservers
            domain_config.save(update_fields=["nameservers"])
            ret.updated_num = 1

        updated_host_aliases = list(set(domain_config.host_aliases) | set(domain_res.hostAliases))
        if updated_host_aliases != domain_config.host_aliases:
            domain_config.host_aliases = updated_host_aliases
            domain_config.save(update_fields=["host_aliases"])
            ret.updated_num = 1
    else:
        DomainResolution.objects.create(
            application=module.application,
            nameservers=domain_res.nameservers,
            host_aliases=domain_res.hostAliases,
        )
        ret.created_num += 1

    return ret
