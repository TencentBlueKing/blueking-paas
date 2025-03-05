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

import logging
from functools import wraps
from pathlib import Path

from bkpaas_auth import get_user_by_user_id
from bkpaas_auth.models import user_id_encoder
from blue_krill.web.std_error import APIError
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.transaction import atomic
from django.utils.translation import gettext as _

from paasng.core.tenant.constants import AppTenantMode
from paasng.core.tenant.user import DEFAULT_TENANT_ID, OP_TYPE_TENANT_ID
from paasng.platform.declarative.application.resources import ApplicationDesc
from paasng.platform.declarative.constants import AppSpecVersion
from paasng.platform.declarative.exceptions import ControllerError, DescriptionValidationError
from paasng.platform.declarative.handlers import get_desc_handler
from paasng.platform.smart_app.services.app_desc import get_app_description
from paasng.platform.smart_app.services.detector import SourcePackageStatReader
from paasng.platform.smart_app.services.dispatch import dispatch_package_to_modules
from paasng.utils.error_codes import error_codes

logger = logging.getLogger("commands")


def handle_error(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except (ControllerError, DescriptionValidationError, APIError) as e:
            self.stderr.write(f"{type(e)}: {e.message}")
        except Exception:
            logger.exception("command error")

    return wrapper


def validate_app_desc(app_desc: ApplicationDesc):
    if app_desc.market is None:
        raise error_codes.FAILED_TO_HANDLE_APP_DESC.f(_("缺失应用市场配置（market)!"))
    if app_desc.spec_version == AppSpecVersion.VER_1:
        raise error_codes.MISSING_DESCRIPTION_INFO.f(_("请检查源码包是否存在 app_desc.yaml 文件"))


class Command(BaseCommand):
    help = "处理 S-Mart 应用包"

    def add_arguments(self, parser):
        parser.add_argument(
            "-f",
            "--file",
            dest="file_",
            required=True,
            type=str,
            help="s-mart 应用包的路径",
        )
        parser.add_argument(
            "-u", "--operator", dest="operator", required=False, type=str, default="admin", help="当前操作人"
        )
        parser.add_argument(
            "--app_tenant_mode",
            dest="app_tenant_mode",
            required=False,
            type=str,
            default=AppTenantMode.GLOBAL,
            help="租户类型",
        )
        parser.add_argument(
            "--app_tenant_id", dest="app_tenant_id", required=False, type=str, default="", help="租户ID"
        )

    @handle_error
    def handle(self, file_: str, operator, app_tenant_mode, app_tenant_id, *args, **options):
        breakpoint()
        filepath = Path(file_)
        operator = get_user_by_user_id(user_id_encoder.encode(settings.USER_TYPE, operator))

        stat = SourcePackageStatReader(filepath).read()
        if not stat.version:
            raise error_codes.MISSING_VERSION_INFO

        # Step 1. create application, module
        validate_app_desc(get_app_description(stat))
        handler = get_desc_handler(stat.meta_info)

        # 需要补充应用的租户信息
        tenant_id = self._get_tenant_id(app_tenant_mode, app_tenant_id)
        stat.meta_info["tenant"] = {
            "app_tenant_mode": app_tenant_mode,
            "app_tenant_id": app_tenant_id,
            "tenant_id": tenant_id,
        }
        with atomic():
            # 由于创建应用需要操作 v2 的数据库, 因此将事务的粒度控制在 handle_app 的维度, 避免其他地方失败导致创建应用的操作回滚, 但是 v2 中 app code 已被占用的问题.
            application = handler.handle_app(operator)

        # Step 2. dispatch package as Image to registry
        with atomic():
            dispatch_package_to_modules(
                application,
                tarball_filepath=filepath,
                stat=stat,
                operator=operator,
                modules=set(handler.app_desc.modules.keys()),
            )
        self.stdout.write("Finish！")

    def _get_tenant_id(self, app_tenant_mode, app_tenant_id):
        """所属租户（tenant_id）是开发者中心自身的逻辑，为减少用户理解成本，可从已有参数中获取"""
        if not settings.ENABLE_MULTI_TENANT_MODE:
            return DEFAULT_TENANT_ID
        if app_tenant_mode == AppTenantMode.GLOBAL:
            return OP_TYPE_TENANT_ID
        return app_tenant_id
