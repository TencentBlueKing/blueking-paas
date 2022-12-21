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
import operator

from django.db.models import Q
from iam.contrib.converter.queryset import DjangoQuerySetConverter
from iam.eval.constants import OP
from six.moves import reduce


class PluginPolicyConverter(DjangoQuerySetConverter):
    def operator_map(self, operator, field, value):
        if field == "plugin.id":
            if operator == OP.EQ:
                return self.eq_plugin_id
            elif operator == OP.IN:
                return self.in_plugin_id
            raise ValueError("invalid op {}".format(operator))
        return None

    def eq_plugin_id(self, field, value):
        """权限中心 EQ 操作符

        :param field: 权限中心字段, 只支持 plugin.id
        :param value: 权限中心策略的值, 当 field == plugin.id 时, 这个值的含义是插件注册到 IAM 中的资源ID
        """
        if field != "plugin.id":
            raise ValueError("invalid field {}".format(field))
        resource_id = value
        pd_id, plugin_id = resource_id.split(":")
        return Q(pd__identifier=pd_id, id=plugin_id)

    def in_plugin_id(self, field, value):
        """权限中心 IN 操作符

        :param field: 权限中心字段, 只支持 plugin.id
        :param value: 权限中心策略的值, 当 field == plugin.id 时, 这个值的含义是多个插件注册到 IAM 中的资源ID列表
        """
        if field != "plugin.id":
            raise ValueError("invalid field {}".format(field))
        if not isinstance(value, (list, tuple)):
            raise ValueError("invalid value {}".format(value))

        qs = []
        for resource_id in value:
            pd_id, plugin_id = resource_id.split(":")
            qs.append(Q(pd__identifier=pd_id, id=plugin_id))
        return reduce(operator.or_, qs)
