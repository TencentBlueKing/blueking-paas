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

from typing import Optional

from django.db.transaction import atomic
from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from paasng.accessories.publish.market import serializers
from paasng.accessories.publish.market.models import MarketConfig, Product, Tag, get_all_corp_products
from paasng.accessories.publish.market.protections import AppPublishPreparer
from paasng.infras.accounts.permissions.application import application_perm_class, check_application_perm
from paasng.infras.iam.permissions.resources.application import AppAction
from paasng.misc.audit.constants import OperationEnum, OperationTarget
from paasng.misc.audit.service import add_app_audit_record
from paasng.platform.applications.mixins import ApplicationCodeInPathMixin
from paasng.platform.applications.models import Application
from paasng.utils.error_codes import error_codes


class ProductBaseViewSet(viewsets.ModelViewSet):
    def get_application(self) -> Optional[Application]:
        raise NotImplementedError

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["application"] = self.get_application()
        return ctx

    def get_queryset(self):
        return Product.objects.owned_and_collaborated_by(self.request.user)


class ProductCreateViewSet(ProductBaseViewSet):
    """
    注册桌面产品
    create: 注册桌面产品
    - [测试地址](/api/market/products)
    list: 获取产品列表
    - [测试地址](/api/market/products)
    """

    def get_application(self) -> Optional[Application]:
        if "application" not in self.request.data:
            return None
        application = get_object_or_404(Application, code=self.request.data["application"])
        check_application_perm(self.request.user, application, AppAction.MANAGE_APP_MARKET)
        return application

    queryset = Product.objects.all()
    serializer_class = serializers.ProductCreateSLZ
    lookup_field = "code"


class ProductCombinedViewSet(ProductBaseViewSet):
    """
    产品属性
    retrieve: 获取产品属性
    - [测试地址](/api/market/products/awesome-app)
    update: 修改产品属性
    - [测试地址](/api/market/products/awesome-app){:target="_blank"}
    """

    queryset = Product.objects.all()
    serializer_class = serializers.ProductCombinedSLZ
    lookup_field = "code"

    def get_application(self) -> Optional[Application]:
        if "code" not in self.kwargs:
            return None
        application = get_object_or_404(Application, code=self.kwargs["code"])
        check_application_perm(self.request.user, application, AppAction.MANAGE_APP_MARKET)
        return application

    def update(self, request, *args, **kwargs):
        partial = request.GET.get("partial", True)
        kwargs["partial"] = partial
        # update() method will fire an "product_create_or_updated" event which triggers
        # market syncing tasks.
        response = super().update(request, *args, **kwargs)
        return response


class TagViewSet(viewsets.ModelViewSet):
    """
    产品分类(按用途)
    list: 获取分类列表
    - [测试地址](/api/market/tags)
    retrieve: 获取分类详细
    - [测试地址](/api/market/tags)
    """

    queryset = Tag.objects.filter(enabled=True).exclude(parent__enabled=False)
    serializer_class = serializers.TagSLZ
    pagination_class = None
    lookup_field = "id"


class ProductStateViewSet(ProductBaseViewSet):
    """
    产品上线状态
    retrieve: 获取产品上线状态
    - [测试地址](/api/market/products/awesome-app/state)
    update: 修改产品上线状态
    - [测试地址](/api/market/products/awesome-app/state)
    """

    queryset = Product.objects.all()
    serializer_class = serializers.ProductStateSLZ
    lookup_field = "code"


class CorpProductViewSet(viewsets.ViewSet):
    """应用在市场绑定业务相关 API"""

    def list(self, request):
        items = get_all_corp_products()
        return Response([item._asdict() for item in items])


class MarketConfigViewSet(viewsets.ModelViewSet, ApplicationCodeInPathMixin):
    """查看与管理应用的市场相关配置"""

    serializer_class = serializers.MarketConfigSLZ
    permission_classes = [IsAuthenticated, application_perm_class(AppAction.MANAGE_APP_MARKET)]

    @swagger_auto_schema(Response={200: serializers.MarketConfigSLZ}, tags=["应用市场"])
    def retrieve(self, request, code):
        """[API] 获取某个应用的市场相关配置"""
        application = self.get_application()
        market_config, _ = MarketConfig.objects.get_or_create_by_app(application)
        serializer = self.serializer_class(market_config)
        return Response(serializer.data)

    @swagger_auto_schema(
        Response={200: serializers.MarketConfigSLZ}, tags=["应用市场"], request_body=serializers.MarketConfigSLZ
    )
    def update(self, request, code):
        """[API] 用于修改某个应用的市场相关配置, 该接口不允许修改应用市场服务开关"""
        application = self.get_application()
        market_config, _ = MarketConfig.objects.get_or_create_by_app(application)
        serializer = self.serializer_class(instance=market_config, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        # 审计记录
        add_app_audit_record(
            app_code=application.code,
            user=request.user.pk,
            action_id=AppAction.MANAGE_APP_MARKET,
            operation=OperationEnum.MODIFY_MARKET_INFO,
            target=OperationTarget.APP,
        )
        return Response(serializer.data)

    def switch(self, request, code):
        """[API] 应用市场服务开关"""
        application = self.get_application()
        # 如果是要关闭发布状态，则不检测是否满足条件
        if request.data["enabled"]:  # noqa: SIM102
            if not AppPublishPreparer(application).all_matched:
                raise error_codes.RELEASED_MARKET_CONDITION_NOT_MET
        # 更新该应用的市场配置的 `enabled` 状态
        MarketConfig.objects.update_enabled(application, request.data["enabled"])

        # 审计记录
        operation = OperationEnum.RELEASE_TO_MARKET if request.data["enabled"] else OperationEnum.OFFLINE_MARKET
        add_app_audit_record(
            app_code=application.code,
            user=request.user.pk,
            action_id=AppAction.MANAGE_APP_MARKET,
            operation=operation,
            target=OperationTarget.APP,
        )
        return Response(self.get_serializer(application.market_config).data)

    @atomic
    @swagger_auto_schema(request_body=serializers.MarketEntranceSLZ, tags=["访问入口"])
    def set_entrance(self, request, code):
        """设置市场访问地址"""
        application = self.get_application()
        market_config, _ = MarketConfig.objects.get_or_create_by_app(application)
        slz = serializers.MarketEntranceSLZ(instance=market_config, data=request.data)
        slz.is_valid(raise_exception=True)
        market_config = slz.save()
        serializer = self.serializer_class(market_config)

        # 审计记录
        add_app_audit_record(
            app_code=application.code,
            user=request.user.pk,
            action_id=AppAction.MANAGE_APP_MARKET,
            operation=OperationEnum.MODIFY_MARKET_URL,
            target=OperationTarget.APP,
        )
        return Response(serializer.data)


class PublishViewSet(viewsets.ViewSet, ApplicationCodeInPathMixin):
    """与发布应用到市场相关 ViewSet"""

    serializer_class = serializers.MarketConfigSLZ
    permission_classes = [IsAuthenticated, application_perm_class(AppAction.MANAGE_APP_MARKET)]

    @swagger_auto_schema(response_serializer=serializers.PublishProtectionSLZ)
    def check_preparations(self, request, code):
        """检查当前发布的准备条件是否已经满足"""
        application = self.get_application()
        status = AppPublishPreparer(application).perform()
        return Response(
            serializers.PublishProtectionSLZ(
                {"all_conditions_matched": not status.activated, "failed_conditions": status.failed_conditions}
            ).data
        )
