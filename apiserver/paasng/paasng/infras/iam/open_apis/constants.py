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
from blue_krill.data_types.enum import StructuredEnum


class MethodType(str, StructuredEnum):
    """
    权限中心拉取资源的 method 参数值
    字段协议说明 https://bk.tencent.com/docs/document/6.0/160/8427?r=1
    """

    LIST_ATTR = "list_attr"
    LIST_ATTR_VALUE = "list_attr_value"
    LIST_INSTANCE = "list_instance"
    FETCH_INSTANCE_INFO = "fetch_instance_info"
    LIST_INSTANCE_BY_POLICY = "list_instance_by_policy"
    SEARCH_INSTANCE = "search_instance"
