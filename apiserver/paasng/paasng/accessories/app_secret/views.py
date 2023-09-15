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

from django.utils.translation import gettext_lazy as _
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from paasng.accessories.app_secret.constants import MAX_SECRET_COUNT
from paasng.accessories.app_secret.serializers import (
    AppSecretIdSLZ,
    AppSecretInEnvVarSLZ,
    AppSecretSLZ,
    AppSecretStatusSLZ,
)
from paasng.accessories.app_secret.utilts import get_deployed_secret_list
from paasng.accessories.iam.permissions.resources.application import AppAction
from paasng.accounts.constants import FunctionType
from paasng.accounts.models import make_verifier
from paasng.accounts.permissions.application import application_perm_class
from paasng.accounts.serializers import VerificationCodeSLZ
from paasng.platform.applications.mixins import ApplicationCodeInPathMixin
from paasng.platform.feature_flags.constants import PlatformFeatureFlag
from paasng.platform.oauth2.api import BkOauthClient
from paasng.platform.oauth2.models import BkAppSecretInEnvVar
from paasng.platform.oauth2.utils import get_app_secret_in_env_var

logger = logging.getLogger(__name__)


class BkAuthSecretViewSet(viewsets.ViewSet, ApplicationCodeInPathMixin):
    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    @swagger_auto_schema(tags=["鉴权信息"], responses={"200": AppSecretSLZ(many=True)})
    def list(self, request, code):
        """
        获取应用的密钥列表
        """
        application = self.get_application()
        secret_list = BkOauthClient().get_app_secret_list(application.code)
        return Response(AppSecretSLZ(secret_list, many=True).data)

    @swagger_auto_schema(tags=["鉴权信息"], responses={"201": "没有返回数据"})
    def create(self, request, code):
        """
        新建密钥
        """
        client = BkOauthClient()
        application = self.get_application()
        secret_list = client.get_app_secret_list(application.code)
        if len(secret_list) >= MAX_SECRET_COUNT:
            raise ValidationError(_(f"密钥已达到上限，应用仅允许有 {MAX_SECRET_COUNT} 个密钥"))

        client.create_app_secret(code)
        return Response(status=status.HTTP_201_CREATED)

    @swagger_auto_schema(tags=["鉴权信息"], request_body=AppSecretStatusSLZ, responses={"204": "没有返回数据"})
    def toggle(self, request, code, bk_app_secret_id):
        """
        启用/禁用密钥
        """
        serializer = AppSecretStatusSLZ(data=request.data)
        serializer.is_valid(raise_exception=True)

        application = self.get_application()
        # 内置密钥不能被禁用
        if not (enabled := serializer.data['enabled']):
            app_secret_in_config_var = get_app_secret_in_env_var(application.code)
            if app_secret_in_config_var.id == int(bk_app_secret_id):
                raise ValidationError(_("当前密钥为内置密钥，不允许被禁用"))

        BkOauthClient().toggle_app_secret(code, bk_app_secret_id, enabled)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(tags=["鉴权信息"], responses={"204": "没有返回数据"})
    def delete(self, request, code, bk_app_secret_id):
        """
        删除密钥
        """
        application = self.get_application()
        client = BkOauthClient()
        # 检查密钥是否已经被禁用，BKAuth 侧删除密钥并不要求密钥已经是禁用状态，所以需要手动检查
        del_secret = client.get_secret_by_id(application.code, bk_app_secret_id)
        if not del_secret:
            raise ValidationError(_("密钥不存在"))

        if del_secret.enabled:
            raise ValidationError(_("密钥状态为：已启用，请先禁用后再删除密钥"))

        # 前面检查禁用时候已经保证不是内置密钥了，不过为了防止有意外的情况这里还是多加一步校验
        app_secret_in_config_var = get_app_secret_in_env_var(application.code)
        if app_secret_in_config_var.id == int(bk_app_secret_id):
            raise ValidationError(_("当前密钥为内置密钥，不允许删除"))

        client.del_app_secret(code, bk_app_secret_id)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(tags=["鉴权信息"], request_body=VerificationCodeSLZ)
    def view_secret_detail(self, request, code, bk_app_secret_id):
        """验证验证码查看密钥详情"""
        application = self.get_application()

        # 部分版本没有发送通知的渠道可通过平台FeatureFlag设置：跳过验证码校验步骤
        if PlatformFeatureFlag.get_default_flags()[PlatformFeatureFlag.VERIFICATION_CODE]:
            serializer = VerificationCodeSLZ(data=request.data)
            serializer.is_valid(raise_exception=True)

            verifier = make_verifier(request.session, FunctionType.GET_APP_SECRET.value)
            is_valid = verifier.validate(serializer.data["verification_code"])
            if not is_valid:
                raise ValidationError({"verification_code": [_("验证码错误")]})
        else:
            logger.warning("Verification code is not currently supported, return app secret directly")

        secret = BkOauthClient().get_secret_by_id(application.code, bk_app_secret_id)
        if not secret:
            raise ValidationError(_("密钥不存在"))

        return Response({"bk_app_secret": secret.bk_app_secret})


class BuiltinSecretViewSet(viewsets.ViewSet, ApplicationCodeInPathMixin):
    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    @swagger_auto_schema(tags=["内置密钥"], responses={"200": AppSecretInEnvVarSLZ})
    def get(self, request, code):
        """查询应用的环境变量默认密钥"""
        application = self.get_application()
        app_secret_in_config_var = get_app_secret_in_env_var(application.code).bk_app_secret
        deployed_secret_list = get_deployed_secret_list(application)

        return Response(
            AppSecretInEnvVarSLZ(
                {"app_secret_in_config_var": app_secret_in_config_var, "deployed_secret_list": deployed_secret_list}
            ).data
        )

    @swagger_auto_schema(tags=["内置密钥"], request_body=AppSecretIdSLZ, responses={"204": "没有返回数据"})
    def rotate(self, request, code):
        """更换应用的内置密钥"""
        application = self.get_application()
        serializer = AppSecretIdSLZ(data=request.data)
        serializer.is_valid(raise_exception=True)
        bk_app_secret_id = serializer.data['id']

        # 检查密钥的状态，已启用的密钥才能设置为内置密钥
        secret = BkOauthClient().get_secret_by_id(application.code, bk_app_secret_id)
        if not secret:
            raise ValidationError(_("密钥不存在"))
        if not secret.enabled:
            raise ValidationError(_("密钥已被禁用，不能设置为内置密钥"))

        BkAppSecretInEnvVar.objects.update_or_create(
            bk_app_code=application.code, defaults={"bk_app_secret_id": bk_app_secret_id}
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
