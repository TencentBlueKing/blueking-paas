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
from blue_krill.data_types.enum import FeatureFlag, FeatureFlagField
from django.conf import settings


class PlatformFeatureFlag(FeatureFlag):  # type: ignore
    ## 仅用于控制前端页面功能展示
    MGRLEGACY = FeatureFlagField(
        label="PaaS2.0 应用迁移，全新部署的版本可不展示该功能", default=settings.ENABLE_MANAGE_LEGACY_APP
    )
    MARKET_VISIBILITY = FeatureFlagField(label="市场可见范围", default=settings.ENABLE_MARKET_VISIBILITY)
    AGGREGATE_SEARCH = FeatureFlagField(label="聚合搜索", default=settings.ENABLE_AGGREGATE_SEARCH)
    DOCUMENT_MANAGEMENT = FeatureFlagField(label="文档管理", default=settings.ENABLE_DOCUMENT_MANAGEMENT)
    DEVELOPMENT_TIME_RECORD = FeatureFlagField(label="记录应用开时长", default=settings.ENABLE_DEVELOPMENT_TIME_RECORD)
    REGION_DISPLAY = FeatureFlagField(label="显示应用版本", default=settings.ENABLE_REGION_DISPLAY)
    ENABLE_IMAGE_APP_BIND_REPO = FeatureFlagField(
        label="镜像应用绑定源码仓库，仅用于 Homepage",
        default=settings.ENABLE_IMAGE_APP_BIND_REPO,
    )
    BK_PLUGIN_TYPED_APPLICATION = FeatureFlagField(
        label="创建与使用“蓝鲸插件”类型应用", default=settings.IS_ALLOW_CREATE_BK_PLUGIN_APP
    )
    # 依赖其他平台的服务
    MONITORING = FeatureFlagField(label="监控告警", default=settings.ENABLE_BK_MONITOR)
    RESOURCE_METRICS = FeatureFlagField(label="应用资源使用率，蓝鲸监控提供数据源", default=settings.ENABLE_BK_MONITOR)
    BK_NOTICE = FeatureFlagField(label="蓝鲸通知公告服务", default=settings.ENABLE_BK_NOTICE)
    ANALYTICS = FeatureFlagField(label="访问统计", default=settings.ENABLE_ANALYSIS)
    CI = FeatureFlagField(label="CI 相关功能，如代码检查", default=settings.ENABLE_CI)
    BK_CI_PIPELINE_BUILD = FeatureFlagField(
        label="蓝盾流水线-云原生应用镜像构建",
        default=bool(settings.BK_CI_PAAS_PROJECT_ID and settings.BK_CI_BUILD_PIPELINE_ID),
    )

    ## Apiserver 会依赖这个特性判断是否发送通知
    VERIFICATION_CODE = FeatureFlagField(label="验证码", default=settings.ENABLE_VERIFICATION_CODE)
