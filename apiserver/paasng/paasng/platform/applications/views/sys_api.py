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

import base64
import logging
import random
import string
from io import BytesIO

from bkpaas_auth.models import user_id_encoder
from django.conf import settings
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.response import Response

from paasng.accessories.publish.sync_market.managers import AppDeveloperManger
from paasng.core.core.storages.object_storage import app_logo_storage
from paasng.core.core.storages.sqlalchemy import legacy_db
from paasng.infras.oauth2.utils import get_oauth2_client_secret
from paasng.infras.sysapi_client.constants import ClientAction
from paasng.infras.sysapi_client.roles import sysapi_client_perm_class
from paasng.platform.applications import serializers as slzs
from paasng.platform.applications.constants import LightApplicationViewSetErrorCode
from paasng.platform.applications.exceptions import IntegrityError, LightAppAPIError
from paasng.platform.applications.models import Application
from paasng.platform.applications.tenant import validate_app_tenant_params
from paasng.platform.applications.utils import create_third_app
from paasng.platform.mgrlegacy.constants import LegacyAppState

try:
    from paasng.infras.legacydb_te.adaptors import AppAdaptor, AppTagAdaptor
    from paasng.infras.legacydb_te.models import get_developers_by_v2_application
except ImportError:
    from paasng.infras.legacydb.adaptors import AppAdaptor, AppTagAdaptor  # type: ignore
    from paasng.infras.legacydb.models import get_developers_by_v2_application  # type: ignore

logger = logging.getLogger(__name__)


class LightAppViewSet(viewsets.ViewSet):
    """为标准运维提供轻应用管理接口，部分代码迁移自 open—paas"""

    permission_classes = [sysapi_client_perm_class(ClientAction.MANAGE_LIGHT_APPLICATIONS)]

    @swagger_auto_schema(request_body=slzs.LightAppCreateSLZ)
    def create(self, request):
        """创建轻应用"""
        slz = slzs.LightAppCreateSLZ(data=request.data)
        if not slz.is_valid():
            raise LightAppAPIError(LightApplicationViewSetErrorCode.PARAM_NOT_VALID, message=slz.errors)

        data = slz.validated_data
        with legacy_db.session_scope() as session:
            app_manager = AppAdaptor(session=session)
            tag_manager = AppTagAdaptor(session=session)
            parent_app = app_manager.get(code=data["parent_app_code"])

            if not parent_app:
                raise LightAppAPIError(
                    LightApplicationViewSetErrorCode.PARAM_NOT_VALID, message="parent_app_code is illegal"
                )

            app_code = self.get_available_light_app_code(session, parent_app.code)
            if not app_code:
                raise LightAppAPIError(
                    LightApplicationViewSetErrorCode.PARAM_NOT_VALID, message="generate app_code failed"
                )

            tag = tag_manager.get(code=data["tag"])
            logo_content = data.get("logo")
            if logo_content:
                logo_url = self.store_logo(app_code, logo_content)
            else:
                logo_url = ""

            app_tenant_mode, app_tenant_id, tenant = validate_app_tenant_params(request.user, data["app_tenant_mode"])
            try:
                light_app = AppAdaptor(session=session).create(
                    code=app_code,
                    name=data["name"],
                    app_tenant_mode=app_tenant_mode,
                    app_tenant_id=app_tenant_id,
                    tenant_id=tenant.id,
                    logo=logo_url,
                    is_lapp=True,
                    creator=data["creator"],
                    tag=tag,
                    height=data.get("height") or parent_app.height,
                    width=data.get("width") or parent_app.width,
                    external_url=data["external_url"],
                    deploy_ver=settings.DEFAULT_REGION_NAME,
                    introduction=data.get("introduction"),
                    state=LegacyAppState.ONLINE.value,
                    is_already_test=1,
                    is_already_online=1,
                )
            except IntegrityError as e:
                logger.exception("Create lapp %s(%s) failed!", data["name"], app_code)
                raise LightAppAPIError(
                    LightApplicationViewSetErrorCode.CREATE_APP_ERROR,
                    message=f"app with the same {e.field} already exists.",
                )
            except Exception as e:
                logger.exception("save app base info fail.")
                raise LightAppAPIError(
                    LightApplicationViewSetErrorCode.CREATE_APP_ERROR, message="create light app failed"
                ) from e

            try:
                AppDeveloperManger(session=session).update_developers(
                    code=light_app.code, target_developers=data["developers"]
                )
            except Exception:
                logger.exception("同步开发者信息到桌面失败！")
                raise LightAppAPIError(
                    LightApplicationViewSetErrorCode.CREATE_APP_ERROR, message="create light app failed"
                )

            return self.make_app_response(session, light_app)

    @swagger_auto_schema(query_serializer=slzs.LightAppDeleteSLZ())
    def delete(self, request):
        """软删除轻应用"""
        slz = slzs.LightAppDeleteSLZ(data=request.query_params)
        if not slz.is_valid():
            raise LightAppAPIError(LightApplicationViewSetErrorCode.PARAM_NOT_VALID, message=slz.errors)

        data = slz.validated_data
        with legacy_db.session_scope() as session:
            app_manager = AppAdaptor(session=session)
            app = self.validate_app(app_manager.get(data["light_app_code"]))

            try:
                app_manager.soft_delete(code=app.code)
            except Exception:
                logger.exception("save app base info fail.")
                raise LightAppAPIError(
                    LightApplicationViewSetErrorCode.CREATE_APP_ERROR, message="create light app failed"
                )

        return self.make_feedback_response(LightApplicationViewSetErrorCode.SUCCESS, data={"count": 1})

    @swagger_auto_schema(request_body=slzs.LightAppEditSLZ)
    def edit(self, request):
        """修改轻应用"""
        slz = slzs.LightAppEditSLZ(data=request.data, partial=True)
        if not slz.is_valid():
            raise LightAppAPIError(LightApplicationViewSetErrorCode.PARAM_NOT_VALID, message=slz.errors)

        data = slz.validated_data
        with legacy_db.session_scope() as session:
            app_manager = AppAdaptor(session=session)
            tag_manager = AppTagAdaptor(session=session)
            app = self.validate_app(app_manager.get(data["code"]))

            tag = tag_manager.get(code=data.pop("tag", None))
            logo_content = data.get("logo")
            if logo_content:
                data["logo"] = self.store_logo(app.code, logo_content)

            if tag:
                data["tags_id"] = tag.id

            developers = data.pop("developers", None)

            try:
                app_manager.update(app.code, data)
            except Exception:
                logger.exception("save app base info fail.")
                raise LightAppAPIError(
                    LightApplicationViewSetErrorCode.CREATE_APP_ERROR, message="edit light app failed"
                )

            if developers:
                try:
                    AppDeveloperManger(session=session).update_developers(code=app.code, target_developers=developers)
                except Exception:
                    logger.exception("同步开发者信息到桌面失败！")
                    raise LightAppAPIError(
                        LightApplicationViewSetErrorCode.CREATE_APP_ERROR, message="create light app failed"
                    )

            return self.make_app_response(session, app)

    @swagger_auto_schema(query_serializer=slzs.LightAppQuerySLZ())
    def query(self, request):
        """查询轻应用"""
        slz = slzs.LightAppQuerySLZ(data=request.query_params)
        if not slz.is_valid():
            raise LightAppAPIError(LightApplicationViewSetErrorCode.PARAM_NOT_VALID, message=slz.errors)

        data = slz.validated_data
        with legacy_db.session_scope() as session:
            app_manager = AppAdaptor(session=session)
            app = self.validate_app(app_manager.get(data["light_app_code"]))

            return self.make_app_response(session, app)

    def handle_exception(self, exc):
        """统一异常处理, 将 LightAppAPIError 转换成 Response"""
        if isinstance(exc, LightAppAPIError):
            return self.make_feedback_response(
                code=exc.error_code,
                message=exc.message,
            )

        return super().handle_exception(exc)

    @classmethod
    def generate_app_maker_code(cls, parent_code):
        """
        生成轻应用 ID
        """
        alphabet = string.digits + string.ascii_lowercase

        # 轻应用的 app code 根据约定长度为 15
        # 为保证可创建的轻应用足够多(至少 36 * 36 个), 至少保留 2 位由随机字符生成
        parent_code = parent_code[:13]
        salt = "".join(random.choices(alphabet, k=15 - len(parent_code)))
        return f"{parent_code}_{salt}"

    @classmethod
    def get_available_light_app_code(cls, session, parent_code, max_times=10):
        app_manager = AppAdaptor(session=session)
        for __ in range(max_times):
            app_code = cls.generate_app_maker_code(parent_code)
            if not app_manager.get(app_code):
                return app_code
        return None

    @staticmethod
    def store_logo(app_code, logo: str):
        """将 base64 编码后的图片存储至 AppLogoStorage, 并刷新 storage 的缓存.
        :param app_code: 轻应用ID
        :param logo: base64 编码后的图片内容
        :return:
        """
        if not logo:
            return ""

        logo_name = f"o_{app_code}.png"  # 轻应用 logo 规则
        logo_file = BytesIO(base64.b64decode(logo))
        app_logo_storage.save(logo_name, logo_file)
        bucket = settings.APP_LOGO_BUCKET
        try:
            from paasng.platform.applications.handlers import initialize_app_logo_metadata

            initialize_app_logo_metadata(Application._meta.get_field("logo").storage, bucket, logo_name)
        except Exception:
            logger.exception("Fail to update logo cache.")
        return app_logo_storage.url(logo_name)

    def make_app_response(self, session, app):
        return self.make_feedback_response(
            LightApplicationViewSetErrorCode.SUCCESS,
            data={
                "light_app_code": app.code,
                "app_name": app.name,
                "app_url": app.external_url,
                "introduction": app.introduction,
                "creator": app.creater,
                "logo": app.logo,
                "developers": sorted(get_developers_by_v2_application(app, session)),
                "state": app.state,
            },
        )

    def make_feedback_response(self, code, data=None, message=""):
        return Response(
            {
                "bk_error_msg": message,
                "bk_error_code": code.value,
                "data": data,
                "result": data is not None,
            }
        )

    @staticmethod
    def validate_app(app):
        if not app or not app.is_lapp:
            raise LightAppAPIError(LightApplicationViewSetErrorCode.PARAM_NOT_VALID, message=f"{app.code} not found")
        return app


class SysAppViewSet(viewsets.ViewSet):
    permission_classes = [sysapi_client_perm_class(ClientAction.MANAGE_APPLICATIONS)]

    @swagger_auto_schema(request_body=slzs.SysThirdPartyApplicationSLZ, tags=["创建第三方(外链)应用"])
    def create_sys_third_app(self, request, sys_id):
        """给特定系统提供的创建第三方应用的 API, 应用ID 必现以系统ID为前缀"""
        serializer = slzs.SysThirdPartyApplicationSLZ(data=request.data, context={"sys_id": sys_id})
        serializer.is_valid(raise_exception=True)
        data = serializer.data

        operator = user_id_encoder.encode(settings.USER_TYPE, data["operator"])

        app_tenant_mode, app_tenant_id, tenant = validate_app_tenant_params(request.user, data["app_tenant_mode"])
        application = create_third_app(
            data["region"],
            data["code"],
            data["name_zh_cn"],
            data["name_en"],
            operator,
            app_tenant_mode,
            app_tenant_id,
            tenant.id,
        )
        # 返回应用的密钥信息
        secret = get_oauth2_client_secret(application.code)
        return Response(
            data={"bk_app_code": application.code, "bk_app_secret": secret},
            status=status.HTTP_201_CREATED,
        )
