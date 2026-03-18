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

import datetime
import logging
from dataclasses import asdict
from typing import Optional

from django.utils.translation import get_language
from sqlalchemy import and_, or_

from paasng.accessories.publish.market.models import Tag
from paasng.accessories.publish.sync_market.models import TagData, TagMap
from paasng.core.tenant.constants import AppTenantMode

try:
    from paasng.infras.legacydb_te.adaptors import (
        AppAdaptor,
        AppDeveloperAdaptor,
        AppEnvVarAdaptor,
        AppOpsAdaptor,
        AppReleaseRecordAdaptor,
        AppSecureInfoAdaptor,
        AppTagAdaptor,
        AppUseRecordAdaptor,
        EngineAppAdaptor,
    )
except ImportError:
    from paasng.infras.legacydb.adaptors import (  # type: ignore
        AppAdaptor,
        AppDeveloperAdaptor,
        AppEnvVarAdaptor,
        AppOpsAdaptor,
        AppReleaseRecordAdaptor,
        AppSecureInfoAdaptor,
        AppTagAdaptor,
        AppUseRecordAdaptor,
        EngineAppAdaptor,
    )

logger = logging.getLogger(__name__)


class AppTagManger(AppTagAdaptor):
    def create_tagmap(self, tag_data: TagData):
        tag_dict = asdict(tag_data)
        # 是否为二级分类
        if tag_data.parent_id:
            parent = TagMap.objects.get(remote_id=tag_data.parent_id).tag
            tag_dict["parent"] = parent
        else:
            tag_dict["parent"] = None
        tag_dict.pop("parent_id", "")
        tag_dict.pop("id", None)
        tag = Tag.objects.create(**tag_dict)

        TagMap.objects.create(tag=tag, remote_id=tag_data.id)
        return True

    def sync_tags_from_console(self):
        """同步应用分类"""
        # 获取应用分类列表，不同版本需要差异化实现
        tag_list = self.get_tag_list()
        for tag in tag_list:
            try:
                rel = TagMap.objects.get(remote_id=tag.id)
                if rel.tag.name != tag.name:
                    old_name = rel.tag.name
                    # 更新分类名称
                    rel.tag.name = tag.name
                    rel.tag.save()
                    logger.info(f"Tag name is updated from {old_name} to {tag.name}")
            except TagMap.DoesNotExist:
                self.create_tagmap(tag)
                logger.info(f"add new tag, name is {tag.name}")

    def get_tag_by_name(self, name: str):
        """根据名称获取 tag 信息"""
        tag = self.session.query(self.model).filter_by(name=name).scalar()
        return tag

    def create_tag(self, tag_data: dict):
        """创建 tag，主要用于单元测试初始化数据"""
        tag = self.model(**tag_data)
        self.session.add(tag)
        return tag


class AppDeveloperManger(AppDeveloperAdaptor):
    """应用开发者"""


class AppOpsManger(AppOpsAdaptor):
    """应用运营者"""


class AppManger(AppAdaptor):
    """应用"""

    def get(self, code: str):
        app = self.session.query(self.model).filter_by(code=code).scalar()
        return app

    def verify_name_is_unique(
        self, name: str, code: Optional[str] = None, field_name: str = "name", app_tenant_id: Optional[str] = None
    ) -> bool:
        qs = self.session.query(self.model)
        if code:
            qs = qs.filter(self.model.code != code)
        if hasattr(self.model, "app_tenant_id"):
            qs = self._narrow_by_tenant(qs, app_tenant_id)
        if field_name == "name_en" and hasattr(self.model, "name_en"):
            app = qs.filter_by(name_en=name).scalar()
        else:
            app = qs.filter_by(name=name).scalar()
        return not app

    def _narrow_by_tenant(self, qs, app_tenant_id: Optional[str]):
        """Narrow the query so that uniqueness is scoped per-tenant while
        also preventing conflicts with global applications.

        Rules:
        - Global apps (app_tenant_id="") must have globally unique names, so
          no filtering is applied.
        - Tenant-specific apps must not collide with apps in the same tenant
          OR with any global app.
        """
        if app_tenant_id is None or app_tenant_id == "":
            return qs

        tenant_filter = self.model.app_tenant_id == app_tenant_id
        global_filter = and_(
            self.model.app_tenant_id == "",
            self.model.app_tenant_mode == AppTenantMode.GLOBAL.value,
        )

        return qs.filter(or_(tenant_filter, global_filter))

    def delete_by_code(self, code: str):
        """根据 code 从 DB 中删除应用"""
        self.session.query(self.model).filter_by(code=code).delete()
        self.session.commit()

    def delete_by_name(self, name: str):
        """根据 name 从 DB 中删除应用"""
        self.session.query(self.model).filter_by(name=name).delete()
        self.session.commit()


class AppUseRecordManger(AppUseRecordAdaptor):
    """应用访问记录"""

    def get_app_records(self, application_codes: list, days_before: int, limit: int):
        dt_before = datetime.date.today() - datetime.timedelta(days=days_before)
        result = self.get_records(application_codes, dt_before, limit)
        if get_language() == "en":
            data = [{"application_code": item[0], "application_name": item[2], "pv": item[3]} for item in result]
        else:
            data = [{"application_code": item[0], "application_name": item[1], "pv": item[3]} for item in result]
        return data


class AppReleaseRecordManger(AppReleaseRecordAdaptor):
    """应用部署记录
    应用正式环境部署成功后将操作记录同步到 console , 这样桌面才能显示：首次上线/提测时间、最近上线时间，并展示最新应用tab
    """


class AppEnvVarManger(AppEnvVarAdaptor):
    """应用自定义环境变量"""


class AppSecureInfoManger(AppSecureInfoAdaptor):
    """应用安全信息,如 DB 信息等"""


class EngineAppManger(EngineAppAdaptor):
    """App engine 中保存的应用信息"""
