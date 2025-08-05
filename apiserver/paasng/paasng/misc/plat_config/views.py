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

from django.conf import settings
from drf_yasg.utils import swagger_auto_schema
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from paas_wl.infras.cluster.constants import BK_LOG_DEFAULT_ENABLED


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
            # 应用令牌，用于 APP 调用用户态的云 API
            "APP_ACCESS_TOKEN": settings.FE_FEATURE_SETTINGS_APP_ACCESS_TOKEN,
            # 是否显示沙箱开发
            "DEV_SANDBOX": settings.FE_FEATURE_SETTINGS_DEV_SANDBOX,
            # 是否展示应用可用性保障
            "APP_AVAILABILITY_LEVEL": settings.FE_FEATURE_SETTINGS_APP_AVAILABILITY_LEVEL,
            # 是否展示 MCP Server 云 API 权限
            "MCP_SERVER_API": settings.FE_FEATURE_SETTINGS_MCP_SERVER_API,
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
            # 访问控制台功能，由是否启用 BCS 控制
            "WEB_CONSOLE": settings.ENABLE_BCS,
            # 是否能创建 LessCode 应用
            "BK_LESSCODE_APP": settings.ENABLE_BK_LESSCODE,
            # 开启了多租户，则应用不能申请 ESB API
            "ESB_API": not settings.ENABLE_MULTI_TENANT_MODE,
            # 是否开启多租户模式
            "MULTI_TENANT_MODE": settings.ENABLE_MULTI_TENANT_MODE,
            # 是否使用蓝鲸日志平台方案
            "BK_LOG": BK_LOG_DEFAULT_ENABLED,
        }
        return Response(data={**features_reuses_backend_settings, **fronted_features})
