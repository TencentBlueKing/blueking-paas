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

from blue_krill.data_types.enum import EnumField, IntStructuredEnum, StrStructuredEnum


class PAMetadataKey(StrStructuredEnum):
    SITE_ID = "bkpa_site_id"


class MetricSourceType(IntStructuredEnum):
    INGRESS = EnumField(1, label="ingress")
    USER_TRACKER = EnumField(2, label="user_tracker")


class MetricsDimensionType(StrStructuredEnum):
    PATH = EnumField("path", label="path")
    USER = EnumField("user", label="user")
    ACTION = EnumField("action", label="action")


class MetricsInterval(StrStructuredEnum):
    """Available interval for metrics"""

    FIVE_MINUTES = EnumField("5m", label="5m")
    ONE_HOUR = EnumField("1h", label="1h")
    ONE_DAY = EnumField("1d", label="1d")
    ONE_WEEK = EnumField("1w", label="1w")
    # None means there is no time period included
    NONE = EnumField("none", label="none")
