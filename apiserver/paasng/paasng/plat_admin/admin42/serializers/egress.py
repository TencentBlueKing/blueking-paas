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
from django.utils.translation import gettext as _
from rest_framework import serializers

from paas_wl.networking.constants import NetworkProtocol


class EgressRuleSLZ(serializers.Serializer):
    host = serializers.CharField(label=_('IP/域名'))
    port = serializers.IntegerField(label=_('端口'))
    protocol = serializers.ChoiceField(label=_('协议'), choices=NetworkProtocol.get_django_choices())


class EgressSpecSLZ(serializers.Serializer):
    replicas = serializers.IntegerField(label=_('副本数量'))
    cpu_limit = serializers.CharField(label=_('CPU 限制'))
    memory_limit = serializers.CharField(label=_('内存限制'))
    rules = serializers.ListField(label=_('规则'), child=EgressRuleSLZ(), min_length=1)
