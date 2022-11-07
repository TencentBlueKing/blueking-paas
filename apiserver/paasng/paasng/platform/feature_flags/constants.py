# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017-2022THL A29 Limited,
a Tencent company. All rights reserved.
Licensed under the MIT License (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the
specific language governing permissions and limitations under the License.

We undertake not to change the open source license (MIT license) applicable

to the current version of the project delivered to anyone in the future.
"""
from blue_krill.data_types.enum import FeatureFlag, FeatureFlagField


class PlatformFeatureFlag(FeatureFlag):
    RESOURCE_METRICS = FeatureFlagField(label="应用资源使用率")
    PHALANX = FeatureFlagField(label="监控告警")
    ANALYTICS = FeatureFlagField(label="访问统计")
    MGRLEGACY = FeatureFlagField(label="应用迁移")
    API_GATEWAY = FeatureFlagField(label="云 API 管理")
    CI = FeatureFlagField(label="CI功能")
    AGGREGATE_SEARCH = FeatureFlagField(label="聚合搜索")
    VERIFICATION_CODE = FeatureFlagField(label='验证码')
    # 只有打开平台级别的 ENABLE_WEB_CONSOLE, 前端才会线上 "打开控制台" 的入口
    ENABLE_WEB_CONSOLE = FeatureFlagField(label="开放 WebConsole", default=True)
    SUPPORT_HTTPS = FeatureFlagField(label="默认所有集群均支持 HTTPS", default=True)
    BK_PLUGIN_TYPED_APPLICATION = FeatureFlagField(label='创建与使用“蓝鲸插件”类型应用', default=False)
