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
from typing import List

from django.db import models
from django.utils.translation import gettext_lazy as _

from paas_wl.bk_app.cnative.specs.crd.bk_app import SvcDiscEntryBkSaaS, HostAlias
from paas_wl.utils.models import AuditedModel
from paasng.utils.models import make_json_field

BkSaaSField = make_json_field("BkSaaSField", List[SvcDiscEntryBkSaaS])
NameServersField = make_json_field("NameServersField", List[str])
HostAliasesField = make_json_field("NameServersField", List[HostAlias])


class SvcDiscConfig(AuditedModel):
    """" 服务发现配置 """

    application_id = models.UUIDField(verbose_name=_('所属应用'), unique=True, null=False)

    bk_saas = BkSaaSField(default=list, help_text="")


class DomainResolution(AuditedModel):
    """ 域名解析配置 """

    application_id = models.UUIDField(verbose_name=_('所属应用'), unique=True, null=False)

    nameservers = NameServersField(default=list, help_text="k8s dnsConfig nameServers")
    host_aliases = HostAliasesField(default=list, help_text="k8s hostAliases")
