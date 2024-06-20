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
from drf_yasg.utils import swagger_auto_schema
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet


class FrontendFeatureViewSet(ViewSet):
    @swagger_auto_schema(tags=["前端特性配置"])
    def get_features(self, request):
        # 仅用于控制前端页面展示的特性
        fronted_features = {
            # 访问统计
            "ANALYTICS": settings.FE_FEATURE_SETTINGS_ANALYTICS,
            # 镜像应用绑定源码仓库
            "IMAGE_APP_BIND_REPO": settings.FE_FEATURE_SETTINGS_IMAGE_APP_BIND_REPO,
            # 显示应用版本
            "REGION_DISPLAY": settings.FE_FEATURE_SETTINGS_REGION_DISPLAY,
            # 记录应用开时长
            "DEVELOPMENT_TIME_RECORD": settings.FE_FEATURE_SETTINGS_DEVELOPMENT_TIME_RECORD,
            # 文档管理
            "DOCUMENT_MANAGEMENT": settings.FE_FEATURE_SETTINGS_DOCUMENT_MANAGEMENT,
            # 聚合搜索
            "AGGREGATE_SEARCH": settings.FE_FEATURE_SETTINGS_AGGREGATE_SEARCH,
            # 市场可见范围
            "MARKET_VISIBILITY": settings.FE_FEATURE_SETTINGS_MARKET_VISIBILITY,
            # PaaS2.0 应用迁移，全新部署的版本可不展示该功能
            "MGRLEGACY": settings.FE_FEATURE_SETTINGS_MGRLEGACY,
            # 云原生应用迁移
            "CNATIVE_MGRLEGACY": settings.FE_FEATURE_SETTINGS_CNATIVE_MGRLEGACY,
            # 应用令牌，用于 APP 调用用户态的 云 API
            "APP_ACCESS_TOKEN": settings.FE_FEATURE_SETTINGS_APP_ACCESS_TOKEN,
        }
        # 部分前端的特性复用了后端的配置
        features_reuses_backend_settings = {
            # 发送验证码
            "VERIFICATION_CODE": settings.ENABLE_VERIFICATION_CODE,
            # 监控告警
            "MONITORING": settings.ENABLE_BK_MONITOR,
            # 应用资源使用率，蓝鲸监控提供数据源
            "RESOURCE_METRICS": settings.ENABLE_BK_MONITOR,
            # 蓝鲸通知公告服务
            "BK_NOTICE": settings.ENABLE_BK_NOTICE,
            # 代码检查
            "CODE_CHECK": bool(settings.CODE_CHECK_CONFIGS),
            # 蓝鲸 CI 流水线构建镜像
            "BK_CI_PIPELINE_BUILD": bool(settings.BK_CI_PAAS_PROJECT_ID and settings.BK_CI_BUILD_PIPELINE_ID),
            # 创建与使用“蓝鲸插件”类型应用
            "BK_PLUGIN_TYPED_APPLICATION": settings.IS_ALLOW_CREATE_BK_PLUGIN_APP,
        }
        return Response(data={**features_reuses_backend_settings, **fronted_features})
