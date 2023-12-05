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
from typing import List

import requests
from bkpaas_auth import get_user_by_user_id
from bkpaas_auth.models import user_id_encoder
from django.conf import settings
from django.core.files.base import ContentFile
from django.utils.translation import gettext as _

from paasng.accessories.publish.market.constant import AppType
from paasng.accessories.publish.sync_market.managers import AppEnvVarManger, AppSecureInfoManger
from paasng.platform.applications.constants import AppLanguage, ApplicationRole
from paasng.platform.mgrlegacy.constants import AppMember, LegacyAppState

logger = logging.getLogger(__name__)


class LegacyAppProxy:
    def __init__(self, legacy_app, session):
        self.legacy_app = legacy_app
        self.session = session

    def is_from_legacy_v1(self) -> bool:
        return False

    def to_paasv3_region(self) -> str:
        """应用 region，目前只支持默认版本"""
        return settings.DEFAULT_REGION_NAME

    def is_smart(self) -> bool:
        """是否为 Smart 应用"""
        return self.legacy_app.is_saas

    def legacy_url(self) -> str:
        """PaaS2.0 上应用的访问地址"""
        if self.is_smart():
            return f"{settings.BK_PAAS2_URL}/saas/info/{self.legacy_app.code}/"
        return f"{settings.BK_PAAS2_URL}/app/info/{self.legacy_app.code}/"

    def is_third_app(self) -> bool:
        return self.legacy_app.is_third

    def _get_app_type(self) -> str:
        """应用类型，用于判断是否可迁移"""
        if self.legacy_app.is_sysapp or self.legacy_app.is_platform:
            return "system_application"
        elif self.legacy_app.is_third:
            return "third_party_application"
        elif self.legacy_app.is_lapp:
            return "qingyingyong"

        return "common_application"

    def is_supported(self) -> list:
        # 支持第三方应用迁移
        if self.is_third_app():
            return []

        # 轻应用暂不支持迁移
        if self._get_app_type() == "qingyingyong":
            return [_("暂不支持轻应用迁移")]

        # 非普通应用
        if self._get_app_type() not in ["common_application"]:
            return [_("暂不支持该类型应用迁移")]

        if self.get_language() != AppLanguage.PYTHON.value:
            return [_("目前仅支持Python应用迁移")]
        return []

    def is_celery_enabled(self):
        return self.legacy_app.is_use_celery

    def is_celery_beat_enabled(self):
        return self.legacy_app.is_use_celery_beat

    def get_source_init_template(self) -> str:
        """初始化模板类型"""
        # 第三方应用不需要设置
        if self.is_third_app():
            return ""

        if self.get_language() == AppLanguage.PYTHON.value:
            return "django_legacy"
        else:
            raise ValueError(self.legacy_app.language)

    def get_language(self) -> str:
        # 第三方应用不需要设置
        if self.is_third_app():
            return ""

        if not self.legacy_app.language:
            return ""

        language_lower = self.legacy_app.language.lower()
        if language_lower in ["python"]:
            return AppLanguage.PYTHON.value
        elif language_lower in ["java"]:
            return AppLanguage.JAVA.value
        else:
            raise ValueError(language_lower)

    def get_secret_key(self):
        """获取应用的 bk_app_secret，所有版本都需要"""
        return self.legacy_app.auth_token

    def get_unified_password(self):
        """app数据库密码（rabbitmq密码）"""
        obj = AppSecureInfoManger(self.session).get(self.legacy_app.code)
        assert obj, "No AppSecureInfo found"

        return obj.db_password

    def get_environment_vars(self):
        env_list = AppEnvVarManger(self.session).list(self.legacy_app.code)
        variables = {item.key: item.value for item in env_list}
        return variables

    def get_logo_url(self):
        return f"{settings.BK_PAAS2_URL}/media/applogo/{self.legacy_app.code}.png"

    def get_logo_filename(self):
        return "%s.png" % self.legacy_app.code

    def get_logo_file(self):
        logo_url = self.get_logo_url()
        try:
            response = requests.get(logo_url, stream=True)
            if response.ok:
                return ContentFile(response.raw.data)
        except Exception:
            logger.exception("从旧版本Paas获取应用Logo失败.")

        logger.info("尝试返回默认logo")
        try:
            # 参考老版本开发者中心的应用列表页面，如果加载不到应用的logo，则使用默认的logo
            response = requests.get(settings.APPLICATION_DEFAULT_LOGO, stream=True)
            if response.ok:
                return ContentFile(response.raw.data)
        except Exception:
            logger.exception("从旧版本Paas获取应用默认Logo失败.")

    def is_prod_deployed(self):
        """已经部署到正式环境，且没有下架"""
        return (
            self.legacy_app.state not in [LegacyAppState.OUTLINE.value, LegacyAppState.DEVELOPMENT.value]
            and self.legacy_app.is_already_online
        )

    def is_stag_deployed(self):
        """已经部署到测试环境，且测试环境没有下架"""
        return self.legacy_app.state not in [LegacyAppState.DEVELOPMENT.value] and self.legacy_app.is_already_test

    def has_prod_deployed(self):
        """prod环境曾经上线过(现在可能下架了，也可能没有)"""
        return bool(self.legacy_app.first_online_time)

    def has_stag_deployed(self):
        """stag 环境曾经上线过(现在可能下架了，也可能没有)"""
        return bool(self.legacy_app.first_test_time)

    def offline_url(self):
        """应用下架页面链接"""
        # smart 应用
        if self.legacy_app.is_saas:
            return f"{settings.BK_PAAS2_URL}/saas/release/offline/{self.legacy_app.code}/"
        else:
            return f"{settings.BK_PAAS2_URL}/release/{self.legacy_app.code}/"

    def get_app_members(self, migration_owner: str) -> List[AppMember]:
        """应用成员列表
        PaaS2.0 的成员信息都在权限中心，且无法根据应用查询成员信息
        所以只将执行迁移的操作者初始化为管理员，再由管理员自行添加成员
        """
        # 将 user_id 转为真实的用户名
        owner_username = get_user_by_user_id(migration_owner, username_only=True).username
        return [AppMember(username=owner_username, role=ApplicationRole.ADMINISTRATOR.value)]  # type: ignore

    def get_app_creator_id(self, migration_owner: str) -> str:
        """应用创建者"""
        # Smart 应用的开发者是"蓝鲸智云"这样的企业账号
        # 所以 Smart 应用的创建者初始化为迁移操作的执行者
        if self.is_smart():
            return migration_owner
        # 普通应用，需要将用户名转成 user_id
        return user_id_encoder.encode(username=self.legacy_app.creater, provider_type=settings.USER_TYPE)

    def get_app_description(self) -> str:
        return ""

    def get_app_type(self) -> int:
        return AppType.THIRD_PARTY.value if self.legacy_app.is_third else AppType.PAAS_APP.value

    def is_app_resizable(self) -> bool:
        return self.legacy_app.is_resize
