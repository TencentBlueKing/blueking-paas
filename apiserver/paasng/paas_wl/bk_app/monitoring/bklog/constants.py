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

# 注解或标签中存储应用名称的键名
BKAPP_NAME_ANNO_KEY = "bkapp.paas.bk.tencent.com/name"
# 注解中存储应用 ID 的键名
BKAPP_CODE_ANNO_KEY = "bkapp.paas.bk.tencent.com/code"
# 注解中存储模块名称的键名
MODULE_NAME_ANNO_KEY = "bkapp.paas.bk.tencent.com/module-name"
# 注解中存储当前部署环境的键名
ENVIRONMENT_ANNO_KEY = "bkapp.paas.bk.tencent.com/environment"
# 注解中存储当前 WlApp 名称的键名
WLAPP_NAME_ANNO_KEY = "bkapp.paas.bk.tencent.com/wl-app-name"


class BkLogConfigType(str, StructuredEnum):
    STD_LOG = EnumField("std_log_config", label="标准输出日志")
    CONTAINER_LOG = EnumField("container_log_config", label="容器日志")
    NODE_LOG = EnumField("node_log_config", label="节点日志")
