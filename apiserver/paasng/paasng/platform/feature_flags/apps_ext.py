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
from django.conf import settings

from paasng.platform.feature_flags.constants import FeatureFlagField, PlatformFeatureFlag

try:
    from paasng.platform.feature_flags.constants_ext import ext_feature_flags
except ImportError:
    ext_feature_flags = [
        FeatureFlagField(name='MGRLEGACY', label='应用迁移', default=settings.ENABLE_MANAGE_LEGACY_APP),
        FeatureFlagField(name='API_GATEWAY', label='云 API 管理', default=True),
        FeatureFlagField(name='MARKET_VISIBILITY', label='市场可见范围', default=True),
        FeatureFlagField(name='RESOURCE_METRICS', label='应用资源使用率', default=False),
        FeatureFlagField(name='PHALANX', label='监控告警', default=False),
        FeatureFlagField(name='ANALYTICS', label='访问统计', default=False),
        FeatureFlagField(name='CI', label='CI功能', default=False),
        FeatureFlagField(name='AGGREGATE_SEARCH', label='聚合搜索', default=False),
        FeatureFlagField(name='VERIFICATION_CODE', label='验证码', default=False),
        FeatureFlagField(name='DOCUMENT_MANAGEMENT', label='文档管理', default=False),
        FeatureFlagField(name='REGION_DISPLAY', label='显示应用版本', default=False),
        FeatureFlagField(name='APP_ID_ALIAS', label='应用标识别名', default=False),
        FeatureFlagField(name='DEVELOPMENT_TIME_RECORD', label='记录应用开时长', default=False),
        FeatureFlagField(name="SUPPORT_HTTPS", label="默认所有集群均支持 HTTPS", default=False),
    ]


def contribute_to_app(app_name: str):
    # 注册额外的平台特性到枚举类中
    for ext_feature_flag in ext_feature_flags:
        PlatformFeatureFlag.register_feature_flag(ext_feature_flag)
