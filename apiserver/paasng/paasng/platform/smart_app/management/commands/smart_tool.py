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
from paasng.core.tenant.utils import global_app_tenant_info, stub_app_tenant_info, validate_app_tenant_info
from paasng.platform.applications.models import SMartAppExtraInfo
from paasng.platform.declarative.application.resources import ApplicationDesc
from paasng.platform.declarative.constants import AppSpecVersion
from paasng.platform.declarative.exceptions import ControllerError, DescriptionValidationError
from paasng.platform.declarative.handlers import get_desc_handler
from paasng.platform.smart_app.services.app_desc import get_app_description
from paasng.platform.smart_app.services.detector import SourcePackageStatReader
from paasng.platform.smart_app.services.dispatch import dispatch_package_to_modules
from paasng.platform.sourcectl.models import SourcePackage
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
            dest="file_path",
            required=True,
            type=str,
            help="s-mart 应用包的路径",
        )
        parser.add_argument(
            "-u", "--operator", dest="operator", required=False, type=str, default="admin", help="当前操作人"
        )
        parser.add_argument(
            "--app_tenant_mode",
            dest="raw_tenant_mode",
            required=False,
            type=str,
            choices=AppTenantMode.get_values(),
            help="租户类型，可选值：global, single",
        )
        parser.add_argument("--app_tenant_id", dest="raw_tenant_id", required=False, type=str, help="租户ID")
        parser.add_argument(
            "--reupload",
            action="store_true",
            help="启用此选项后，将强制覆盖已上传的同名包（判断依据为包的 sha256 签名是否一致）。默认情况下，不重复上传。",
        )

    @handle_error
    def handle(self, file_path: str, operator, raw_tenant_mode, raw_tenant_id, reupload, *args, **options):
        filepath = Path(file_path)
        operator = get_user_by_user_id(user_id_encoder.encode(settings.USER_TYPE, operator))

        stat = SourcePackageStatReader(filepath).read()
        if not stat.version:
            raise error_codes.MISSING_VERSION_INFO

        if SourcePackage.objects.filter(pkg_sha256_signature=stat.sha256_signature).exists():
            if not reupload:
                self.stdout.write("S-Mart package already exists (SHA-256 signature match). Skipping upload！")
                return

            self.stdout.write("S-Mart package found (SHA-256 signature match), proceeding with re-upload.")

        # Step 1. create application, module
        original_app_desc = get_app_description(stat)
        validate_app_desc(original_app_desc)

        handler = get_desc_handler(stat.meta_info)

        # 如果参数中没有指定租户信息，则根据是否开启多租户获取默认值
        if not raw_tenant_mode and not raw_tenant_id:
            app_tenant_info = global_app_tenant_info() if settings.ENABLE_MULTI_TENANT_MODE else stub_app_tenant_info()
        else:
            app_tenant_info = validate_app_tenant_info(raw_tenant_mode, raw_tenant_id)

        stat.meta_info["tenant"] = {
            "app_tenant_mode": app_tenant_info.app_tenant_mode,
            "app_tenant_id": app_tenant_info.app_tenant_id,
            "tenant_id": app_tenant_info.tenant_id,
        }
        with atomic():
            # 由于创建应用需要操作 v2 的数据库, 因此将事务的粒度控制在 handle_app 的维度, 避免其他地方失败导致创建应用的操作回滚, 但是 v2 中 app code 已被占用的问题.
            application = handler.handle_app(operator)
            # 创建/更新 SMartAppExtraInfo, 记录应用原始 code
            SMartAppExtraInfo.objects.update_or_create(
                app=application, defaults={"original_code": original_app_desc.code, "tenant_id": application.tenant_id}
            )

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
