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

from blue_krill.data_types.enum import EnumField, StrStructuredEnum


class ClusterSource(StrStructuredEnum):
    """集群来源"""

    BCS = EnumField("bcs", "BCS 集群")
    NATIVE_K8S = EnumField("native_k8s", "原生 K8S 集群")


class ClusterAuthType(StrStructuredEnum):
    """集群认证类型"""

    TOKEN = EnumField("token", "Token")
    CERT = EnumField("cert", "证书")


class TolerationOperator(StrStructuredEnum):
    """容忍度运算符"""

    EQUAL = EnumField("Equal", "Equal")
    EXISTS = EnumField("Exists", "Exists")


class TolerationEffect(StrStructuredEnum):
    """容忍度效果"""

    NO_EXECUTE = EnumField("NoExecute", "不执行")
    NO_SCHEDULE = EnumField("NoSchedule", "不调度")
    PREFER_NO_SCHEDULE = EnumField("PreferNoSchedule", "倾向不调度")
