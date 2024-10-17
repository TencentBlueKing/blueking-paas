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

from paasng.utils.enum import IntEnum

ANNOT_SERVER_SNIPPET = "nginx.ingress.kubernetes.io/server-snippet"
ANNOT_CONFIGURATION_SNIPPET = "nginx.ingress.kubernetes.io/configuration-snippet"
ANNOT_REWRITE_TARGET = "nginx.ingress.kubernetes.io/rewrite-target"
ANNOT_SSL_REDIRECT = "nginx.ingress.kubernetes.io/ssl-redirect"
# 由于 tke 集群默认会为没有绑定 CLB 的 Ingress 创建并绑定公网 CLB 的危险行为，
# bcs-webhook 会对下发/更新配置时没有指定 clb 的 Ingress 进行拦截，在关闭 tke 集群的 l7-lb-controller 组件后
# 可以在下发 Ingress 时候添加注解 bkbcs.tencent.com/skip-filter-clb: "true" 以跳过 bcs-webhook 的拦截
# l7-lb-controller 状态查询：kubectl get deploy l7-lb-controller -n kube-system
ANNOT_SKIP_FILTER_CLB = "bkbcs.tencent.com/skip-filter-clb"

# Annotations managed by system
reserved_annotations = {
    ANNOT_SERVER_SNIPPET,
    ANNOT_CONFIGURATION_SNIPPET,
    ANNOT_REWRITE_TARGET,
    ANNOT_SSL_REDIRECT,
    ANNOT_SKIP_FILTER_CLB,
}


class AppDomainSource(IntEnum):
    # "BUILT_IN" is reserved for the default ingress's domain, it looks like '{engine_app_name}.apps.com'
    BUILT_IN = 1
    # Auto-generated sub-domains
    AUTO_GEN = 2
    INDEPENDENT = 3


class AppSubpathSource(IntEnum):
    DEFAULT = 1
