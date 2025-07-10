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

import abc
import itertools
import logging
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from functools import lru_cache, reduce
from typing import Any, Collection, Dict, Generator, Iterable, List, Optional, Set, Tuple, Type, Union, cast

from bkpaas_auth import get_user_by_user_id
from bkpaas_auth.models import user_id_encoder
from blue_krill.data_types.enum import IntStructuredEnum
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import gettext as _
from rest_framework.fields import get_attribute
from sqlalchemy import func
from sqlalchemy.orm import Query, Session

from paasng.accessories.publish.market.models import MarketConfig, Tag
from paasng.core.core.storages.sqlalchemy import legacy_db
from paasng.core.region.models import get_region
from paasng.core.tenant.user import get_init_tenant_id
from paasng.infras.accounts.models import Oauth2TokenHolder, UserProfile
from paasng.infras.iam.permissions.resources.application import ApplicationPermission
from paasng.plat_admin.system.constants import SimpleAppSource
from paasng.plat_admin.system.legacy import LegacyAppNormalizer, query_concrete_apps
from paasng.platform.applications.constants import ApplicationType
from paasng.platform.applications.models import Application
from paasng.platform.modules.constants import SourceOrigin
from paasng.platform.sourcectl.controllers.bk_svn import SvnRepoController
from paasng.platform.sourcectl.models import GitProject
from paasng.platform.sourcectl.repo_controller import BaseGitRepoController
from paasng.platform.sourcectl.source_types import get_sourcectl_names, get_sourcectl_type
from paasng.platform.sourcectl.svn.server_config import get_bksvn_config
from paasng.utils.text import basic_str_format

try:
    from paasng.infras.legacydb_te.models import LApplication, LApplicationUseRecord
except ImportError:
    from paasng.infras.legacydb.models import LApplication, LApplicationUseRecord

try:
    from paasng.accessories.paas_analysis.services import get_pv_uv_for_env
except ImportError:

    def get_pv_uv_for_env(*args, **kwargs) -> Tuple[int, int]:  # type: ignore
        """Return a fake value when paas_analysis module is not provided"""
        return -1, -1


RE_QQ = re.compile(r"^\d{5,}$")

PV_UV_COUNT_PERIOD_LENGTH = 90

logger = logging.getLogger(__name__)


class DeployStatus(IntStructuredEnum):
    PRODUCTION = 1
    STAGING = 2
    DEVELOPING = 3
    OFFLINED = 4


@lru_cache()
def count_all_app_visit_record_30days():
    """统计所有应用的访问次数"""
    use_time_gte = datetime.now() - timedelta(days=30)
    with legacy_db.session_scope() as session:
        return Counter(
            dict(
                session.query(LApplication.code, func.count(LApplicationUseRecord.id))
                .join(LApplicationUseRecord)
                .filter(LApplicationUseRecord.use_time >= use_time_gte)
                .group_by(LApplication.code)
                .all()
            )
        )


@dataclass
class SimpleApp:
    """An universal app model which is compatible with both legacy and default PaaS"""

    _source: SimpleAppSource
    name: str
    type: str
    region: str
    code: str
    developers: List[str]
    created: datetime
    deploy_status: DeployStatus
    source_origin: int  # Module property, only read the default module
    source_repo_type: Optional[str]
    source_location: str
    engine_enabled: bool
    creator: str
    # 市场信息
    market_address: Optional[str]
    market_tag: Optional[str]
    # 访问量
    pv: Optional[int] = 0
    uv: Optional[int] = 0
    last_deployed_date: Optional[datetime] = None

    def app_visit_count_30days(self):
        return count_all_app_visit_record_30days()[self.code]


@dataclass
class Contribution:
    project_total_lines: Union[int, str]
    user_total_lines: Union[int, str]
    project_commit_nums: Union[int, str]
    user_commit_nums: Union[int, str]


class AppDataBuilder(metaclass=abc.ABCMeta):
    """Abstract class of AppDataBuilder"""

    @abc.abstractmethod
    def set_filter_developers(self, filter_developers: Collection[str]):
        raise NotImplementedError

    @abc.abstractmethod
    def set_filter_app_codes(self, filter_app_codes: Collection[str]):
        raise NotImplementedError

    @abc.abstractmethod
    def get_results(self) -> Generator[SimpleApp, None, None]:
        raise NotImplementedError


class DefaultAppDataBuilder(AppDataBuilder):
    """Build app data for default platform"""

    def __init__(self, include_pv_uv: bool = False, include_market_info: bool = False):
        self.include_pv_uv = include_pv_uv
        self.include_market_info = include_market_info

        self.apps = Application.objects.filter(is_active=True).exclude(type=ApplicationType.ENGINELESS_APP.value)

        self.filter_developers_enabled = False
        self.filter_developers_app_ids: Set[str] = set()

        self.filter_app_codes_enabled = False
        self.filter_app_codes: Set[str] = set()

    @staticmethod
    def get_deploy_status(app: Application) -> DeployStatus:
        """Return app's deploy status"""
        # TODO: respect multiple modules
        module = app.get_default_module()
        stag_env = module.envs.get(environment="stag")
        prod_env = module.envs.get(environment="prod")

        if prod_env.is_offlined:
            return DeployStatus.OFFLINED
        elif prod_env.is_running():
            return DeployStatus.PRODUCTION
        elif stag_env.is_running():
            return DeployStatus.STAGING
        return DeployStatus.DEVELOPING

    @staticmethod
    def get_pv_uv(app: Application) -> Tuple[int, int]:
        module = app.get_default_module()
        stag_env = module.envs.get(environment="stag")
        prod_env = module.envs.get(environment="prod")

        end_date = date.today()
        start_date = end_date - timedelta(days=PV_UV_COUNT_PERIOD_LENGTH)

        if prod_env.is_running():
            return get_pv_uv_for_env(prod_env, start_date=start_date, end_date=end_date)
        elif stag_env.is_running():
            return get_pv_uv_for_env(stag_env, start_date=start_date, end_date=end_date)
        return 0, 0

    @staticmethod
    def get_tag_display_name(app: Application):
        try:
            extra_info = app.extra_info
        except ObjectDoesNotExist:
            return "--"

        if not extra_info.tag:
            return "--"

        return extra_info.tag.get_name_display()

    @staticmethod
    def get_market_address(application: Application) -> Optional[str]:
        """获取市场访问地址，兼容精简版应用。普通应用如未打开市场开关，返回 None"""
        region = get_region(application.region)
        addr = basic_str_format(
            region.basic_info.link_production_app, {"code": application.code, "region": application.region}
        )
        if not application.engine_enabled:
            return addr

        # Only works for apps whose market config is enabled
        market_config, _ = MarketConfig.objects.get_or_create_by_app(application)
        if not market_config.enabled:
            return None
        return addr

    def set_filter_developers(self, filter_developers: Collection[str]):
        """Set filter by developers"""
        app_filters, app_ids = [], []
        for username in filter_developers:
            # FIXME: 多租户的情况下可能无法正常工作, 考虑持久化租户信息?
            if f := ApplicationPermission().gen_develop_app_filters(username, get_init_tenant_id()):
                app_filters.append(f)

        if app_filters:
            filters = reduce(lambda x, y: x | y, app_filters)
            app_ids = Application.objects.filter(filters).values_list("id", flat=True)

        # Enable filter flag
        self.filter_developers_enabled = True
        self.filter_developers_app_ids = set(app_ids)

    def set_filter_app_codes(self, filter_app_codes: Collection[str]):
        """Set filter by app codes"""
        # Enable filter flag
        self.filter_app_codes_enabled = True
        self.filter_app_codes = set(filter_app_codes)

    def exclude_unqualified(self, apps: Iterable[Application]) -> Generator[Application, None, None]:
        """Exclude unqualified applications"""
        for app in apps:
            if self.filter_developers_enabled and app.pk not in self.filter_developers_app_ids:
                continue
            if self.filter_app_codes_enabled and app.code not in self.filter_app_codes:
                continue

            yield app

    def get_results(self) -> Generator[SimpleApp, None, None]:
        """Return simple apps as result"""
        for app in self.exclude_unqualified(self.apps.order_by("created")):
            engine_enabled = app.engine_enabled
            if engine_enabled:
                deploy_status = self.get_deploy_status(app)
                source_obj = app.get_source_obj()
                if not source_obj:
                    logger.warning("No source object found for application %s", app.code)
                    continue

                source_repo_type: Optional[str] = source_obj.get_source_type()
                source_location = source_obj.get_repo_url() or ""
            else:
                deploy_status = DeployStatus.DEVELOPING
                source_repo_type = None
                source_location = ""

            creator = get_user_by_user_id(app.creator, username_only=True).username

            pv, uv = self.get_pv_uv(app=app) if self.include_pv_uv else (0, 0)

            market_address = market_tag = None
            if self.include_market_info:
                market_address = self.get_market_address(app)
                market_tag = self.get_tag_display_name(app)

            default_module = app.get_default_module()
            item = SimpleApp(
                _source=SimpleAppSource.DEFAULT,
                name=app.name,
                type=app.type,
                region=app.region or "unknown",
                code=app.code,
                created=app.created,
                deploy_status=deploy_status,
                source_origin=default_module.source_origin,
                source_repo_type=source_repo_type,
                source_location=source_location,
                engine_enabled=engine_enabled,
                creator=creator,
                developers=app.get_developers(),
                # 市场信息
                market_address=market_address,
                market_tag=market_tag,
                # 访问量统计
                pv=pv,
                uv=uv,
                last_deployed_date=app.last_deployed_date,
            )
            yield item


class LegacyAppDataBuilder(AppDataBuilder):
    """Build app data for legacy platform"""

    def __init__(self, include_market_info: bool = False):
        self.include_market_info = include_market_info

        self.filter_developers_enabled = False
        self.filter_developers_devs: Set[str] = set()

        self.filter_app_codes_enabled = False
        self.filter_app_codes: Set[str] = set()

    def get_default_qs(self, session: Session) -> Query:
        return query_concrete_apps(session, LApplication).order_by(LApplication.created_date.desc())

    @staticmethod
    def get_deploy_status(app) -> DeployStatus:
        """Return app's deploy status"""
        # 应用开发状态 == 0 时, 代表已经手动下线, 优先级最高
        if app.state == 0:
            return DeployStatus.OFFLINED
        if app.is_already_online:
            return DeployStatus.PRODUCTION
        if app.is_already_test:
            return DeployStatus.STAGING
        return DeployStatus.DEVELOPING

    @staticmethod
    def get_market_address(region: str, app_code: str):
        context = {
            "code": app_code,
            "region": region,
        }
        return get_region(region).basic_info.link_production_app.format(**context)

    @staticmethod
    def get_tag_display_name(tag_id: int) -> str:
        tag = Tag.objects.filter(tagmap__remote_id=tag_id).first()
        return tag.get_name_display() if tag else "--"

    def set_filter_developers(self, filter_developers: Collection[str]):
        self.filter_developers_enabled = True
        self.filter_developers_devs = set(filter_developers)

    def set_filter_app_codes(self, filter_app_codes: Collection[str]):
        self.filter_app_codes_enabled = True
        self.filter_app_codes = set(filter_app_codes)

    def get_results(self) -> Generator[SimpleApp, None, None]:
        """Return simple apps as result"""
        session = legacy_db.get_scoped_session()
        qs = self.get_default_qs(session)
        for app in qs.all():
            deploy_status = self.get_deploy_status(app)

            normalizer = LegacyAppNormalizer(app)
            region = normalizer.get_region()
            if not region:
                continue
            # Skip collections type app
            if app.code.startswith("collection_"):
                continue

            developers = normalizer.get_developers()
            if self.filter_app_codes_enabled and app.code not in self.filter_app_codes:
                continue
            if self.filter_developers_enabled and not (self.filter_developers_devs & set(developers)):
                continue

            if hasattr(app, "svn_domain"):
                source_location = f"svn://{app.svn_domain}:80/apps/{app.code}"
            else:
                source_location = ""

            market_address = market_tag = None
            if self.include_market_info:
                market_address = self.get_market_address(region=region, app_code=app.code)
                market_tag = self.get_tag_display_name(app.tags_id)

            sim_app = SimpleApp(
                _source=SimpleAppSource.LEGACY,
                name=app.name,
                type="legacy",
                region=region,
                code=app.code,
                created=app.created_date,
                deploy_status=deploy_status,
                source_origin=SourceOrigin.AUTHORIZED_VCS.value,
                source_repo_type="bk_svn",
                source_location=source_location,
                engine_enabled=True,
                creator=normalizer.get_creator(),
                developers=developers,
                market_address=market_address,
                market_tag=market_tag,
            )
            yield sim_app


class Table:
    """Table for data representation"""

    def __init__(self, columns: List["Column"]):
        self.columns = columns
        self.rows: List[Any] = []
        self._indented = 0
        self.metadata: Dict[str, Any] = {}

        # Process auto map columns
        self._allowed_row_attrs = set()
        for col in self.columns:
            if isinstance(col, AutoMapperColumn):
                self._allowed_row_attrs.add(col.row_attr_name)

    def set_indent(self, size: int):
        self._indented = size

    def add_row(self, row: List[Any], **row_attrs):
        """Append a row to table"""
        row_data = []
        iter_row = iter(row)
        for i, col in enumerate(self.columns):
            if isinstance(col, AutoMapperColumn) and col.row_attr_name in row_attrs:
                obj = row_attrs[col.row_attr_name]
                row_value = get_attribute(obj, col.field_name.split("."))
            else:
                row_value = next(iter_row)

            # If current column should be indented, set the value to empty string
            if i < self._indented:
                row_value = ""

            row_data.append(row_value)
        self.rows.append(row_data)


class Column:
    display_name: str

    def format_value(self, value: Any) -> str:
        return str(value)


class AutoMapperColumn(Column):
    row_attr_name: str = NotImplemented
    field_name: str = NotImplemented


class AppColumn(AutoMapperColumn):
    row_attr_name = "app"


class ColUsername(Column):
    display_name = "用户名"


class ColCreatedAppsCnt(Column):
    display_name = "创建应用个数"


class ColDevAppsCnt(Column):
    display_name = "参与研发应用个数"


class ColAppName(AppColumn):
    field_name = "name"
    display_name = "应用名称"


class ColAppType(AppColumn):
    field_name = "type"
    display_name = "应用类型"


class ColAppCode(AppColumn):
    field_name = "code"
    display_name = "Code"


class ColAppSource(AppColumn):
    field_name = "_source"
    display_name = "平台版本"

    def format_value(self, value: Any) -> str:
        _text_map = {
            SimpleAppSource.LEGACY: "旧版",
            SimpleAppSource.DEFAULT: "v3",
        }
        return _text_map[value]


class ColAppRegion(AppColumn):
    field_name = "region"
    display_name = "部署环境"


class ColAppEngineEnabled(AppColumn):
    field_name = "engine_enabled"
    display_name = "是否开启应用引擎"

    def format_value(self, value: Any) -> str:
        return "是" if value else "否"


class ColAppSourceOrigin(AppColumn):
    field_name = "source_origin"
    display_name = "源码来源"

    def format_value(self, value: Any) -> str:
        return SourceOrigin.get_choice_label(value)


class ColAppSourceRepoType(AppColumn):
    field_name = "source_repo_type"
    display_name = "源码类型"

    def format_value(self, value: Any) -> str:
        try:
            display_info = get_sourcectl_type(value).display_info
            return str(display_info.name)
        except KeyError:
            return "未知"


class ColAppSourceUrl(AppColumn):
    field_name = "source_location"
    display_name = "源码地址"


class ColAppDeployStatus(AppColumn):
    field_name = "deploy_status"
    display_name = "部署状态"

    def format_value(self, value: Any) -> str:
        _text_map = {
            DeployStatus.DEVELOPING: _("未上线"),
            DeployStatus.PRODUCTION: _("已上线"),
            DeployStatus.OFFLINED: _("已下架"),
            DeployStatus.STAGING: _("测试中"),
        }
        return _text_map[value]


class ColAppMarketAddress(AppColumn):
    field_name = "market_address"
    display_name = "市场地址"


class ColAppMarketTag(AppColumn):
    field_name = "market_tag"
    display_name = "市场标签"


class ColAppCreator(AppColumn):
    field_name = "creator"
    display_name = "创建者"


class ColAppDevelopers(AppColumn):
    field_name = "developers"
    display_name = "开发者"

    def format_value(self, value: Any) -> str:
        return ", ".join(sorted(value))


class ColAppCreatedAt(AppColumn):
    field_name = "created"
    display_name = "创建时间"

    def format_value(self, value: Optional[datetime]) -> str:
        return value.strftime("%Y-%m-%d %H:%M") if value else "-"


class ColAppUseRecord(AppColumn):
    field_name = "app_visit_count_30days"
    display_name = "30d 桌面累积访问次数"


class ColAppPV(AppColumn):
    field_name = "pv"
    display_name = f"{PV_UV_COUNT_PERIOD_LENGTH} 天内访问数（PV）"


class ColAppUV(AppColumn):
    field_name = "uv"
    display_name = f"{PV_UV_COUNT_PERIOD_LENGTH} 天内独立访客数（UV）"


class ColAppLastDeployTime(AppColumn):
    field_name = "last_deployed_date"
    display_name = "最近部署时间"

    def format_value(self, value: datetime) -> str:
        if value is None:
            return "--"
        return value.strftime("%Y-%m-%d %H:%M")


class ContributionColumn(AutoMapperColumn):
    row_attr_name = "contribution"


class ColProjectCodeLineNumsColumn(ContributionColumn):
    field_name = "project_total_lines"
    display_name = "项目代码总行数"


class ColUserCodeLineNumsColumn(ContributionColumn):
    field_name = "user_total_lines"
    display_name = "用户代码总行数"


class ColProjectCommitNumsColumn(ContributionColumn):
    field_name = "project_commit_nums"
    display_name = "项目总提交次数"


class ColUserCommitNumsColumn(ContributionColumn):
    field_name = "user_commit_nums"
    display_name = "用户总提交次数"


def uniq_apps(apps: Iterable[SimpleApp]) -> Generator[SimpleApp, None, None]:
    """Return de-duplicated apps, check uniqueness by app.code"""
    seen_app_codes = set()
    for app in apps:
        if app.code in seen_app_codes:
            logger.warning("app %s was duplicated", app.code)
            continue

        seen_app_codes.add(app.code)
        yield app


def group_apps_by_developers(
    filter_developers: Optional[List[str]] = None,
) -> Generator[Tuple[str, Dict[str, Any], List[SimpleApp]], None, None]:
    """Return apps grouped by user, include both legacy and default apps

    :param filter_developers: only include apps which was developed by given users
    """
    g_apps = defaultdict(list)
    g_infos: Dict[str, Dict[str, int]] = {}
    filter_developers = filter_developers or []

    legacy_builder = LegacyAppDataBuilder()
    default_builder = DefaultAppDataBuilder()
    if filter_developers:
        legacy_builder.set_filter_developers(filter_developers)
        default_builder.set_filter_developers(filter_developers)

    merged_apps = uniq_apps(itertools.chain(legacy_builder.get_results(), default_builder.get_results()))
    for app in merged_apps:
        # Skip app without engine
        if not app.engine_enabled:
            continue

        users = app.developers

        for user in users:
            g_apps[user].append(app)
            g_infos.setdefault(user, {"created_count": 0, "count": 0})["count"] += 1

            if app.creator == user:
                g_infos[user]["created_count"] += 1

    def app_sort_key(app):
        return (app._source, app.deploy_status.value, app.code)

    for user, info in sorted(g_infos.items(), key=lambda item: item[1]["count"], reverse=True):
        # Respect filter_developers settings
        if filter_developers and user not in filter_developers:
            continue

        apps = g_apps[user]
        apps.sort(key=app_sort_key)
        yield user, info, apps


def calculate_user_contribution_in_app(username: str, app: SimpleApp):
    # None type check
    if not app.source_repo_type:
        raise RuntimeError("No repo provided")

    repo_admin_credentials = get_bksvn_config(name=app.source_repo_type).get_admin_credentials()
    user_credentials = {}

    if app.source_repo_type in get_sourcectl_names().filter_by_basic_type("git"):
        project = GitProject.parse_from_repo_url(app.source_location, sourcectl_type=app.source_repo_type)
        profile = UserProfile.objects.get(user=user_id_encoder.encode(settings.USER_TYPE, username))
        token_holder = profile.token_holder.get_by_project(project)
        user_credentials["oauth_token"] = token_holder.access_token
        user_credentials["scope_list"] = [token_holder.get_scope()]
        # 用于 refresh token, 通过 oauth_token 无法反查 token_holder
        user_credentials["__token_holder"] = token_holder

    type_spec = get_sourcectl_type(app.source_repo_type)
    repo_info = type_spec.config_as_arguments()

    if app.source_repo_type == get_sourcectl_names().bk_svn:
        svn_cls = cast(Type[SvnRepoController], type_spec.repo_controller_class)
        svn_ctl = svn_cls(repo_admin_credentials=repo_admin_credentials, repo_url=app.source_location)
        return svn_ctl.get_client().rclient.calculate_user_contribution(username)
    elif app.source_repo_type in get_sourcectl_names().filter_by_basic_type("git"):
        git_cls = cast(Type[BaseGitRepoController], type_spec.repo_controller_class)
        git_ctl = git_cls(
            repo_url=app.source_location, user_credentials=user_credentials, api_url=repo_info["api_url"]
        )
        return git_ctl.get_client().calculate_user_contribution(
            username, GitProject.parse_from_repo_url(app.source_location, sourcectl_type=app.source_repo_type)
        )
    return None


def make_table_apps_grouped_by_developer(filter_developers: Optional[List[str]] = None) -> Table:
    """导出特定开发者的应用详情信息，按开发者与应用总数降序排列

    :param filter_developers: 只展示指定开发者的相关数据
    """
    table = Table(
        columns=[
            ColUsername(),
            ColDevAppsCnt(),
            # Below are simple-app related rows
            ColAppName(),
            ColAppCode(),
            ColAppType(),
            ColAppSource(),
            ColAppRegion(),
            ColAppDeployStatus(),
            ColAppCreator(),
            ColAppCreatedAt(),
            ColAppSourceOrigin(),
            ColAppSourceRepoType(),
            ColAppSourceUrl(),
            # Below are contribution related rows
            ColProjectCodeLineNumsColumn(),
            ColUserCodeLineNumsColumn(),
            ColProjectCommitNumsColumn(),
            ColUserCommitNumsColumn(),
        ]
    )

    for user, info, apps in group_apps_by_developers(filter_developers=filter_developers):
        row_data = [user, info["count"]]
        for app in apps:
            contribution = Contribution("--", "--", "--", "--")
            try:
                logger.info("start calculate_user_contribution_in_app for user:%s, app:%s", user, app.code)
                contribution = Contribution(**calculate_user_contribution_in_app(user, app))
                logger.info("finish calculate_user_contribution_in_app for user:%s, app:%s", user, app.code)
            except (Oauth2TokenHolder.DoesNotExist, UserProfile.DoesNotExist):
                logger.exception("Can't find Oauth2TokenHolder for user: %s", user)
            except Exception:
                logger.exception("Unexpected exception")
            table.add_row(row_data, app=app, contribution=contribution)
            # Hide first two columns after the first row was added
            table.set_indent(2)
        table.set_indent(0)
    return table


def make_table_apps_grouped_by_developer_simple(filter_developers: Optional[List[str]] = None) -> Table:
    """导出特定开发者的应用详情信息，按开发者与应用总数降序排列

    - 不包含应用源码与贡献度相关

    :param filter_developers: 只展示指定开发者的相关数据
    """
    table = Table(
        columns=[
            ColUsername(),
            ColCreatedAppsCnt(),
            ColDevAppsCnt(),
            # Below are simple-app related rows
            ColAppName(),
            ColAppCode(),
            ColAppType(),
            ColAppSource(),
            ColAppRegion(),
            ColAppDeployStatus(),
            ColAppCreator(),
            ColAppCreatedAt(),
        ]
    )

    users_cnt_created = 0
    users_cnt_developed = 0

    for user, info, apps in group_apps_by_developers(filter_developers=filter_developers):
        row_data = [user, info["created_count"], info["count"]]
        users_cnt_developed += 1
        if info["created_count"] > 0:
            users_cnt_created += 1

        for app in apps:
            table.add_row(row_data, app=app)
            # Hide first two columns after the first row was added
            table.set_indent(2)
        table.set_indent(0)

    table.metadata = {
        "users_cnt_total": len(filter_developers) if filter_developers else -1,
        "users_cnt_created": users_cnt_created,
        "users_cnt_developed": users_cnt_developed,
    }
    return table


def make_table_apps_basic_info(
    filter_app_codes: Optional[Collection[str]] = None, include_pv_uv: bool = False
) -> Table:
    """导出特定应用的基本信息，包括创建者、开发者、创建时间等

    :param filter_app_codes: 指定需要导出的应用 Code 列表，为 None 时获取所有应用
    :param include_pv_uv: 结果是否包含 PV 与 UV 数据
    """
    columns: List["Column"] = [
        ColAppName(),
        ColAppCode(),
        ColAppType(),
        ColAppSource(),
        ColAppRegion(),
        ColAppEngineEnabled(),
        ColAppSourceOrigin(),
        ColAppSourceRepoType(),
        ColAppSourceUrl(),
        ColAppCreator(),
        ColAppDevelopers(),
        ColAppCreatedAt(),
        ColAppUseRecord(),
        ColAppDeployStatus(),
    ]
    if include_pv_uv:
        columns += [ColAppPV(), ColAppUV()]

    table = Table(columns=columns)
    legacy_builder = LegacyAppDataBuilder()
    default_builder = DefaultAppDataBuilder(include_pv_uv=include_pv_uv, include_market_info=False)

    if filter_app_codes is not None:
        legacy_builder.set_filter_app_codes(filter_app_codes)
        default_builder.set_filter_app_codes(filter_app_codes)

    apps = uniq_apps(itertools.chain(legacy_builder.get_results(), default_builder.get_results()))
    app_codes_with_data = set()
    for app in apps:
        table.add_row([], app=app)
        app_codes_with_data.add(app.code)

    missing_app_codes = set()
    if filter_app_codes is not None:
        missing_app_codes = set(filter_app_codes) - app_codes_with_data
    table.metadata = {
        "missing_app_codes": missing_app_codes,
    }
    return table


def print_table(table: Table, sep: str = "\t", stream=sys.stdout):
    """Print table to console"""
    titles = [str(col.display_name) for col in table.columns]
    print(sep.join(titles), file=stream)

    for row in table.rows:
        str_row = []
        for i, col in enumerate(table.columns):
            str_row.append(col.format_value(row[i]))
        print(sep.join(str_row), file=stream)
