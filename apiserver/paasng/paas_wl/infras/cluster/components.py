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

from typing import Any, Dict, List

from paas_wl.infras.cluster.constants import BK_LOG_DEFAULT_ENABLED, ClusterComponentName


def get_default_component_configs() -> List[Dict[str, Any]]:
    """获取默认组件配置"""

    # 蓝鲸 Ingress Nginx
    bk_ingress_nginx = {"name": ClusterComponentName.BK_INGRESS_NGINX, "required": True}
    # 云原生应用 Operator
    bkpaas_app_operator = {"name": ClusterComponentName.BKPAAS_APP_OPERATOR, "required": True}
    # 开发者中心日志采集器
    bkapp_log_collection = {"name": ClusterComponentName.BKAPP_LOG_COLLECTION, "required": True}
    # 蓝鲸日志平台采集器
    bk_log_collector = {"name": ClusterComponentName.BKAPP_LOG_COLLECTION, "required": False}
    # BCS 提供的通用 Pod 自动扩缩容
    bcs_general_pod_autoscaler = {"name": ClusterComponentName.BCS_GENERAL_POD_AUTOSCALER, "required": False}

    # 如果走蓝鲸日志平台采集方案，则 bk_log_collector 组件必选，bkapp_log_collection 组件非必选
    if BK_LOG_DEFAULT_ENABLED:
        bk_log_collector["required"] = True
        bkapp_log_collection["required"] = False
        return [
            bk_ingress_nginx,
            bkpaas_app_operator,
            bk_log_collector,
            bkapp_log_collection,
            bcs_general_pod_autoscaler,
        ]

    return [
        bk_ingress_nginx,
        bkpaas_app_operator,
        bkapp_log_collection,
        bcs_general_pod_autoscaler,
    ]
