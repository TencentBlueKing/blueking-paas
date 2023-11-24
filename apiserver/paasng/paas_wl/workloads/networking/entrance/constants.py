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


class AppDomainSource(int, StructuredEnum):
    # "BUILT_IN" is reserved for the default ingress's domain, it looks like '{engine_app_name}.apps.com'
    BUILT_IN = 1
    # Auto-generated sub-domains
    AUTO_GEN = 2
    INDEPENDENT = 3


class AppSubpathSource(int, StructuredEnum):
    DEFAULT = 1


class AddressType(str, StructuredEnum):
    """Address types, different value means different source. For example, "custom"
    means the address was provided by a custom domain created by user.
    """

    SUBDOMAIN = "subdomain"
    SUBPATH = "subpath"
    CUSTOM = "custom"
    LEGACY = "legacy"
