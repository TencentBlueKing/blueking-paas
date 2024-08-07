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
import logging
from typing import Set

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from drf_yasg.utils import swagger_auto_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from paas_wl.infras.cluster.constants import ClusterFeatureFlag
from paas_wl.infras.cluster.shim import get_application_cluster
from paasng.accessories.log.models import CustomCollectorConfig
from paasng.accessories.log.serializers import (
    BkLogCustomCollectMetadataOutputSLZ,
    BkLogCustomCollectMetadataQuerySLZ,
    ModuleCustomCollectorConfigSLZ,
)
from paasng.infras.accounts.permissions.application import application_perm_class
from paasng.infras.bk_log.client import make_bk_log_management_client
from paasng.infras.bkmonitorv3.shim import get_or_create_bk_monitor_space
from paasng.infras.iam.permissions.resources.application import AppAction
from paasng.platform.applications.mixins import ApplicationCodeInPathMixin
from paasng.platform.applications.models import Application
from paasng.utils.error_codes import error_codes

logger = logging.getLogger(__name__)


def get_all_builtin_config_names(application: Application) -> Set[str]:
    """get all builtin custom collector config name for application"""
    names = set()
    for module in application.modules.all():
        builtin_config_names = list(
            CustomCollectorConfig.objects.filter(module=module, is_builtin=True).values_list("name_en", flat=True)
        )
        names.update(builtin_config_names)
    return names


class CustomCollectorConfigViewSet(ViewSet, ApplicationCodeInPathMixin):
    """日志采集规则配置视图"""

    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    def get_serializer_context(self):
        """
        Extra context provided to the serializer class.
        """
        application = self.get_application()
        monitor_space, _ = get_or_create_bk_monitor_space(application)
        return {
            "request": self.request,
            "format": self.format_kwarg,
            "view": self,
            "builtin_config_names": sorted(get_all_builtin_config_names(application)),
            "space_uid": monitor_space.space_uid,
        }

    @swagger_auto_schema(
        query_serializer=BkLogCustomCollectMetadataQuerySLZ,
        response_serializer=BkLogCustomCollectMetadataOutputSLZ,
        tags=["日志采集"],
    )
    def get_metadata(self, request, code, module_name):
        """查询在日志平台已创建的自定义上报配置以及日志平台的访问地址"""
        application = self.get_application()
        cluster = get_application_cluster(application)
        if not cluster.has_feature_flag(ClusterFeatureFlag.ENABLE_BK_LOG_COLLECTOR):
            # 集群未开启日志平台特性, 则直接返回，不再调用监控日志平台相关 API
            raise error_codes.CUSTOM_COLLECTOR_UNSUPPORTED

        module = self.get_module_via_path()
        slz = BkLogCustomCollectMetadataQuerySLZ(data=request.query_params)
        slz.is_valid(raise_exception=True)
        monitor_space, _ = get_or_create_bk_monitor_space(module.application)
        cfgs = make_bk_log_management_client().list_custom_collector_config(
            biz_or_space_id=monitor_space.iam_resource_id
        )
        if not slz.validated_data.get("all", False):
            # 过滤当前模块已创建的自定义采集配置 以及 应用所有内置自定义采集配置
            existed_ids = set(
                CustomCollectorConfig.objects.filter(
                    Q(module=module) | Q(is_builtin=True, module__application_id=application.pk)
                ).values_list("collector_config_id", flat=True)
            )
            cfgs = [cfg for cfg in cfgs if cfg.id not in existed_ids]
        return Response(
            data=BkLogCustomCollectMetadataOutputSLZ(
                {
                    "options": cfgs,
                },
                context=self.get_serializer_context(),
            ).data
        )

    @swagger_auto_schema(response_serializer=ModuleCustomCollectorConfigSLZ(many=True), tags=["日志采集"])
    def list(self, request, code, module_name):
        """查询模块日志采集配置"""
        module = self.get_module_via_path()
        qs = CustomCollectorConfig.objects.filter(module=module).order_by("-created")
        return Response(data=ModuleCustomCollectorConfigSLZ(qs, many=True, context=self.get_serializer_context()).data)

    @swagger_auto_schema(
        response_serializer=ModuleCustomCollectorConfigSLZ,
        request_body=ModuleCustomCollectorConfigSLZ,
        tags=["日志采集"],
    )
    def upsert(self, request, code, module_name):
        """更新或创建模块日志采集配置"""
        module = self.get_module_via_path()
        slz = ModuleCustomCollectorConfigSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        validated_data = slz.validated_data

        monitor_space, _ = get_or_create_bk_monitor_space(module.application)
        cfg = make_bk_log_management_client().get_custom_collector_config_by_name_en(
            biz_or_space_id=monitor_space.iam_resource_id, collector_config_name_en=validated_data["name_en"]
        )
        if not cfg or cfg.id != validated_data["collector_config_id"]:
            if CustomCollectorConfig.objects.filter(module=module, name_en=validated_data["name_en"]).exists():
                logger.warning(
                    "CustomCollectorConfig<name_en=%d> is not existed in bk-log!", validated_data["name_en"]
                )
            raise error_codes.CUSTOM_COLLECTOR_NOT_EXISTED.f(
                f"collector_config_id = {validated_data['collector_config_id']}"
            )

        collector_config, _ = CustomCollectorConfig.objects.update_or_create(
            module=module,
            name_en=cfg.name_en,
            defaults={
                "collector_config_id": cfg.id,
                "index_set_id": cfg.index_set_id,
                "bk_data_id": cfg.bk_data_id,
                "log_paths": validated_data["log_paths"],
                "log_type": validated_data["log_type"],
            },
        )
        return Response(
            data=ModuleCustomCollectorConfigSLZ(collector_config, context=self.get_serializer_context()).data
        )

    @swagger_auto_schema(tags=["日志采集"])
    def destroy(self, request, code, module_name, name_en):
        module = self.get_module_via_path()
        cfg = get_object_or_404(CustomCollectorConfig, module=module, name_en=name_en)
        if cfg.is_builtin:
            raise error_codes.CANNOT_DELETE_CUSTOM_COLLECTOR.f(_("内置采集规则只能停用, 不能删除"))
        cfg.delete()
        return Response()

    @swagger_auto_schema(tags=["日志采集"])
    def get_builtin_config(self, request, code, module_name, log_type):
        """获取平台内置的对应类型的日志采集配置
        :param log_type: 日志类型，可选项：json、stdout，在paasng.infras.bk_log.constatns.BkLogType 中定义的类型
        """
        module = self.get_module_via_path()
        try:
            # 业务逻辑保证了模块下一种类型的内置采集规则最多只有一个，name_en 中包含了 log_type
            builtin_log_config = CustomCollectorConfig.objects.get(module=module, is_builtin=True, log_type=log_type)
        except ObjectDoesNotExist:
            raise error_codes.CUSTOM_COLLECTOR_NOT_EXISTED.f(_("平台内置日志采集规则"))

        return Response(
            data=ModuleCustomCollectorConfigSLZ(builtin_log_config, context=self.get_serializer_context()).data
        )
