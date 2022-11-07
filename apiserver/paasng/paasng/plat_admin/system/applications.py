# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017-2022THL A29 Limited,
a Tencent company. All rights reserved.
Licensed under the MIT License (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the
specific language governing permissions and limitations under the License.

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
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import QuerySet

from paasng.engine.models.operations import ModuleEnvironmentOperations
from paasng.platform.applications.models import Application, ModuleEnvironment, UserApplicationFilter
from paasng.platform.core.storages.sqlalchemy import legacy_db
from paasng.publish.sync_market.managers import AppDeveloperManger

from .constants import SimpleAppSource
from .legacy import LegacyAppNormalizer, query_concrete_apps

try:
    from paasng.platform.legacydb_te.models import LApplication
except ImportError:
    from paasng.platform.legacydb.models import LApplication


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
    code: str
    logo_url: str
    developers: List[str]
    created: datetime.datetime
    creator: str

    _db_object: Optional[Any] = None

    def get_source(self) -> int:
        return self._source.value


def get_simple_app_by_default_app(app: Application) -> UniSimpleApp:
    developers = [u.username for u in app.get_developers()]

    simple_app = UniSimpleApp(
        _source=SimpleAppSource.DEFAULT,
        region=app.region or 'unknown',
        name=app.name,
        code=app.code,
        logo_url=app.get_logo_url(),
        created=app.created,
        creator=str_username(app.creator),
        developers=developers,
        _db_object=app,
    )
    return simple_app


def get_simple_app_by_legacy_app(app: LApplication) -> Optional[UniSimpleApp]:
    normalizer = LegacyAppNormalizer(app)
    region = normalizer.get_region()
    if not region:
        return None

    simple_app = UniSimpleApp(
        _source=SimpleAppSource.LEGACY,
        region=region,
        name=app.name,
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
class AppContactInfo:
    """Information for contacting application"""

    latest_operator: Optional[User]
    recent_deployment_operators: List[User]


def get_contact_info(application: Application) -> AppContactInfo:
    """Get application's contact info"""
    try:
        latest_operator = application.latest_op.operation.user
    except ObjectDoesNotExist:
        latest_operator = None

    # 获取距离最近操作时间一个月内，仍然在部署应用的用户
    recent_deployment_operators = query_recent_deployment_operators(application.module_operations, days_range=31)
    return AppContactInfo(latest_operator=latest_operator, recent_deployment_operators=recent_deployment_operators)


def get_env_recent_deployment_ops(env: ModuleEnvironment) -> List[User]:
    """Get environment's recent deployment operators"""
    return query_recent_deployment_operators(env.module_operations, days_range=31)


def query_recent_deployment_operators(operations: QuerySet, days_range: int) -> List[User]:
    """Query latest deployment operators within given days

    :param days_range: the max days range until the latest deployment operation
    """
    try:
        latest_deployment_operation = operations.latest("created")
        earliest_date = latest_deployment_operation.created - datetime.timedelta(days=days_range)
        return list(operations.filter(created__gte=earliest_date).values_list("operator", flat=True).distinct())
    except ModuleEnvironmentOperations.DoesNotExist:
        return []
