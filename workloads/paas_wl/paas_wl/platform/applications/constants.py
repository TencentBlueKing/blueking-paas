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
from blue_krill.data_types.enum import EnumField, StructuredEnum


class AppOperationType(int, StructuredEnum):
    """All types of application operation"""

    CREATE_APPLICATION = 1
    REGISTER_PRODUCT = 4
    MODIFY_PRODUCT_ATTRIBUTES = 5
    PROCESS_START = 6
    PROCESS_STOP = 7
    RECYCLE_ONLINE_RESOURCE = 8
    DELETE_APPLICATION = 9

    OFFLINE_APPLICATION_STAG_ENVIRONMENT = 11
    OFFLINE_APPLICATION_PROD_ENVIRONMENT = 12

    DEPLOY_APPLICATION = 14
    CREATE_MODULE = 15
    DELETE_MODULE = 16

    OFFLINE_MARKET = 10
    RELEASE_TO_MARKET = 17


class WlAppType(str, StructuredEnum):
    """type of workloads app"""

    DEFAULT = EnumField('default')  # 默认类型：无任何定制逻辑

    # 云原生架构应用：完全基于 YAML 模型的应用，当前作为一个独立应用类型存在，但未来它也许会成为所有应用
    # （比如基于 buildpack 的“普通应用”）统一底层架构。到那时，再来考虑如何处置这个类型吧
    CLOUD_NATIVE = EnumField('cloud_native')


class ApplicationType(str, StructuredEnum):
    """Application types, copied from "apiserver" """

    DEFAULT = EnumField('default')
    ENGINELESS_APP = EnumField('engineless_app')
    BK_PLUGIN = EnumField('bk_plugin')
    CLOUD_NATIVE = EnumField('cloud_native')
