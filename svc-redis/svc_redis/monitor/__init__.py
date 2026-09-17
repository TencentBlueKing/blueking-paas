# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
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

"""Redis 增强服务实例指标暴露.

出数方式: 把 prometheus collector 注册到项目已有的 /metrics 采集入口, 每次 scrape 实时采集.

仅覆盖已分配, 未回收且套餐开启 monitor 的实例; 指标取不到时显式缺失, 不用 0 冒充健康.
"""

from svc_redis.monitor.collector import collector_registry

__all__ = ["collector_registry"]
