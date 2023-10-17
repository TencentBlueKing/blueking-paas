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
"""Applications related stuff
"""
import datetime
from dataclasses import dataclass
from typing import Any, Collection, Dict, List, Optional

from bkpaas_auth import get_user_by_user_id
from bkpaas_auth.models import BasicUser, User
from django.conf import settings
from django.db.models import Q
from django.utils.translation import get_language

from paasng.accessories.publish.sync_market.managers import AppDeveloperManger
from paasng.core.core.storages.sqlalchemy import legacy_db
from paasng.platform.applications.models import Application, UserApplicationFilter

from .constants import SimpleAppSource
from .legacy import LegacyAppNormalizer, query_concrete_apps

try:
    from paasng.infras.legacydb_te.adaptors import AppAdaptor
    from paasng.infras.legacydb_te.models import LApplication
except ImportError:
    from paasng.infras.legacydb.adaptors import AppAdaptor  # type: ignore
    from paasng.infras.legacydb.models import LApplication


# Util function for get username for User obj
def str_username(user: User):
    """Util function for get username from User obj"""
    return get_user_by_user_id(user, username_only=True).username


@dataclass
class UniSimpleApp:
    """An universal app model which is compatible with both legacy and default PaaS"""

    _source: SimpleAppSource
    region: str
    name: str
    name_en: str
    code: str
    logo_url: str
    developers: List[str]
    created: datetime.datetime
    creator: str

    _db_object: Optional[Any] = None

    def get_source(self) -> int:
        return self._source.value


def get_simple_app_by_default_app(app: Application) -> UniSimpleApp:
    simple_app = UniSimpleApp(
        _source=SimpleAppSource.DEFAULT,
        region=app.region or 'unknown',
        name=app.name,
        name_en=app.name_en,
        code=app.code,
        logo_url=app.get_logo_url(),
        created=app.created,
        creator=str_username(app.creator),
        developers=app.get_developers(),
        _db_object=app,
    )
    return simple_app


def get_simple_app_by_legacy_app(app: LApplication) -> Optional[UniSimpleApp]:
    normalizer = LegacyAppNormalizer(app)
    region = normalizer.get_region()
    if not region:
        return None

    # Compatible with some versions of APP in PaaS2.0 without name_en field
    name_en = getattr(app, 'name_en', app.name)

    simple_app = UniSimpleApp(
        _source=SimpleAppSource.LEGACY,
        region=region,
        name=app.name,
        name_en=name_en,
        code=app.code,
        logo_url=normalizer.get_logo_url(),
        created=app.created_date,
        creator=normalizer.get_creator(),
        developers=normalizer.get_developers(),
        _db_object=app,
    )
    return simple_app


def query_uni_apps_by_ids(ids: List[str]) -> Dict[str, UniSimpleApp]:
    """Query universal applications by app ids, it will combine the results of both default and legacy platforms"""
    results = query_default_apps_by_ids(ids)

    # Only query missing app ids on legacy platform
    missing_ids = set(ids) - set(results)
    if missing_ids:
        results.update(query_legacy_apps_by_ids(missing_ids))
    return results


def query_default_apps_by_ids(ids: Collection[str]) -> Dict[str, UniSimpleApp]:
    """Query applications by application ids, returns universal model"""
    apps = Application.objects.filter(code__in=ids, is_active=True).select_related('product')

    results = {}
    for app in apps:
        results[app.code] = get_simple_app_by_default_app(app)
    return results


def query_legacy_apps_by_ids(ids: Collection[str]) -> Dict[str, UniSimpleApp]:
    """Query legacy applications by application ids, return universal model"""
    results = {}
    with legacy_db.session_scope() as session:
        apps = query_concrete_apps(session, LApplication).filter(LApplication.code.in_(ids))
        for app in apps:
            simple_app = get_simple_app_by_legacy_app(app)
            if simple_app is not None:
                results[app.code] = simple_app
    return results


def query_uni_apps_by_username(username: str) -> List[UniSimpleApp]:
    """Query universal applications by username, it will combine the results of both default and legacy platforms"""
    default_apps = query_default_apps_by_username(username)
    legacy_apps = query_legacy_apps_by_username(username)
    return default_apps + legacy_apps


def query_default_apps_by_username(username: str) -> List[UniSimpleApp]:
    user = BasicUser(settings.USER_TYPE, username)
    applications = UserApplicationFilter(user).filter()

    results = []
    for app in applications:
        results.append(get_simple_app_by_default_app(app))
    return results


def query_legacy_apps_by_username(username: str) -> List[UniSimpleApp]:
    results = []
    with legacy_db.session_scope() as session:
        apps = AppDeveloperManger(session).get_apps_by_developer(username)

        for app in apps:
            uni_simle_app = get_simple_app_by_legacy_app(app)
            if uni_simle_app is not None:
                results.append(uni_simle_app)
    return results


@dataclass
class UniMinimalApp:
    """Minimal information for application"""

    code: str
    name: str


def query_uni_apps_by_keyword(keyword: str, offset: int, limit: int) -> List[UniMinimalApp]:
    """Query application basic info by keywords (APP ID, APP Name)

    :param keyword: APP ID or APP Name
    :param offset: the offset of the query
    :param limit: the limit of the query
    """
    # 应用名称的字段需要根据请求语言来确定
    language = get_language()
    name_field = 'name_en' if language == "en" else 'name'

    # 蓝鲸统一的规范，默认排序为字母顺序，而不是按最近创建时间排序
    default_apps = Application.objects.all().order_by('code')
    if keyword:
        default_apps = default_apps.filter(Q(code__icontains=keyword) | Q(name__icontains=keyword))

    apps_list = [
        UniMinimalApp(code=app['code'], name=app[name_field]) for app in default_apps.values('code', name_field)
    ]
    # 如果应用数量大于请求数，则直接返回，不再查询 legacy app
    if default_apps.count() > (offset + limit):
        return apps_list

    with legacy_db.session_scope() as session:
        legacy_apps = AppAdaptor(session=session).get_by_keyword(keyword)
    apps_list.extend([UniMinimalApp(code=app['code'], name=app[name_field]) for app in legacy_apps])

    return apps_list
