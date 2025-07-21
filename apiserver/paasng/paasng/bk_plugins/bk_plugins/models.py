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
from typing import Collection, Dict, Iterator, List, Mapping, Optional, Tuple, Union

from bkpaas_auth import get_user_by_user_id
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models import QuerySet
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from pydantic import BaseModel, PrivateAttr

from paasng.accessories.publish.entrance.exposer import env_is_deployed
from paasng.accessories.publish.market.utils import ModuleEnvAvailableAddressHelper
from paasng.bk_plugins.bk_plugins.constants import PluginTagIdType
from paasng.core.tenant.fields import tenant_id_field_factory
from paasng.infras.accounts.utils import id_to_username
from paasng.platform.applications.models import Application, BaseApplicationFilter, ModuleEnvironment
from paasng.platform.engine.configurations.env_var.entities import EnvVariableList, EnvVariableObj
from paasng.platform.engine.configurations.provider import env_vars_providers
from paasng.utils.models import AuditedModel, OwnerTimestampedModel, TimestampedModel

logger = logging.getLogger(__name__)

# Database models start


class BkPluginProfileManager(models.Manager):
    """Custom manager for `BkPluginProfile`"""

    def get_or_create_by_application(self, plugin_app: Application) -> Tuple["BkPluginProfile", bool]:
        """Get the profile object or create a new one

        :return: (<profile object>, created)
        """
        try:
            # Try get `.bk_plugin_profile` directly instead of using `get_or_create()` because it enabled
            # the caller from optimizing queries by using prefetch_related().
            return plugin_app.bk_plugin_profile, False
        except ObjectDoesNotExist:
            # Use application's creator as contact by default
            creator = id_to_username(plugin_app.creator)
            return super().create(
                application=plugin_app, introduction="", contact=creator, tenant_id=plugin_app.tenant_id
            ), True


class BkPluginProfile(OwnerTimestampedModel):
    """Profile which storing extra information for BkPlugins"""

    application = models.OneToOneField(
        Application, on_delete=models.CASCADE, db_constraint=False, related_name="bk_plugin_profile"
    )
    introduction = models.CharField("插件简介", help_text="插件简介", null=True, blank=True, max_length=512)
    contact = models.CharField("联系人", help_text="使用 ; 分隔的用户名", null=True, blank=True, max_length=128)
    tag = models.ForeignKey(
        "BkPluginTag",
        verbose_name="插件分类",
        help_text="选填",
        on_delete=models.SET_NULL,
        db_constraint=False,
        null=True,
        blank=True,
    )

    # Field related API Gateway resource
    api_gw_name = models.CharField(
        "已绑定的 API 网关名称",
        help_text="为空时表示从未成功同步过，暂无已绑定网关",
        null=True,
        blank=True,
        max_length=32,
    )
    api_gw_id = models.IntegerField("已绑定的 API 网关 ID", null=True)
    api_gw_last_synced_at = models.DateTimeField("最近一次同步网关的时间", null=True)

    # 预设的插件使用方，创建插件时指定的插件使用方
    # 在插件部署、或者用户手动在基本信息页面修改插件使用方信息时，才会在 APIGW 上创建网关并给插件使用方授权
    pre_distributor_codes = models.JSONField("预设的插件使用方的 code 列表", blank=True, null=True)
    tenant_id = tenant_id_field_factory()

    objects = BkPluginProfileManager()

    @property
    def code(self) -> str:
        return self.application.code

    @property
    def is_synced(self) -> bool:
        """Plugin's API Gateway resource has been synced or not"""
        return bool(self.api_gw_id)

    @property
    def pre_distributors(self) -> Optional[Collection["BkPluginDistributor"]]:
        if not self.pre_distributor_codes:
            return None
        return BkPluginDistributor.objects.filter(code_name__in=self.pre_distributor_codes)

    def get_tag_info(self) -> Optional[dict]:
        """Plugin's tag information, expected to be returned in the API for plugin list and basic info"""
        if self.tag:
            return self.tag.to_dict()
        return None

    def mark_synced(self, id: int, name: str):
        """Mark current plugin's API Gateway resource was successfully synced

        :param id: id of API Gateway resource, determined by external API Gateway service
        :param name: name of API Gateway
        """
        self.api_gw_id = id
        self.api_gw_name = name
        self.api_gw_last_synced_at = timezone.now()
        self.save()


class BkPluginDistributor(TimestampedModel):
    """A "Distributor" is responsible for providing a collection of BkPlugins to a group of users,
    A plugin's developers can decide that whether the plugin was accessible from a distributor.

    [multi-tenancy] This model is not tenant-aware.
    """

    name = models.CharField("名称", help_text="插件使用方名称", max_length=32, unique=True)
    code_name = models.CharField(
        "英文代号", help_text="插件使用方的英文代号，可替代主键使用", max_length=32, unique=True
    )
    bk_app_code = models.CharField(
        "蓝鲸应用代号", help_text="插件使用方所绑定的蓝鲸应用代号", max_length=20, unique=True
    )
    introduction = models.CharField("使用方简介", null=True, blank=True, max_length=512)

    plugins = models.ManyToManyField(Application, db_constraint=False, related_name="distributors")

    def __str__(self) -> str:
        return f"{self.name} - [{self.code_name}]{self.bk_app_code}"


class BkPluginTag(AuditedModel):
    """Plugins and applications use different markets, and plugins should have their own separate tags

    [multi-tenancy] This model is not tenant-aware.
    """

    name = models.CharField("分类名称", help_text="插件使用方名称", max_length=32, unique=True)
    code_name = models.CharField("分类英文名称", help_text="分类英文名称，可替代主键使用", max_length=32, unique=True)
    priority = models.IntegerField("优先级", default=0, help_text="数字越大，优先级越高")

    def __str__(self) -> str:
        return f"{self.name} - [{self.code_name}]"

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name, "code_name": self.code_name, "priority": self.priority}

    class Meta:
        ordering = ["-priority", "name"]


# Database models end


@env_vars_providers.register_env
def get_plugin_env_variables(env: ModuleEnvironment) -> EnvVariableList:
    """Get env vars for a bk-plugin object"""
    application = env.module.application
    if not is_bk_plugin(application):
        return EnvVariableList()

    profile = application.bk_plugin_profile
    return EnvVariableList(
        [
            EnvVariableObj.with_sys_prefix(
                key="BK_PLUGIN_APIGW_NAME",
                value=profile.api_gw_name or "",
                description=_("插件已绑定的 API 网关名称"),
            )
        ]
    )


class BkPlugin(BaseModel):
    """Type for representing a bk plugin"""

    id: str
    region: str
    name: str
    code: str
    logo_url: str
    has_deployed: bool
    creator: str
    created: datetime.datetime
    updated: datetime.datetime
    tag_info: Optional[dict] = None

    _application = PrivateAttr()

    def __init__(self, application: Application, *args, **kwargs):
        self._application = application
        super().__init__(*args, **kwargs)

    @classmethod
    def from_application(cls, application: Application) -> "BkPlugin":
        creator = get_user_by_user_id(application.creator, username_only=True).username
        try:
            bk_plugin_profile = application.bk_plugin_profile
        except ObjectDoesNotExist:
            tag_info = None
        else:
            tag_info = bk_plugin_profile.get_tag_info()

        return BkPlugin(
            application,
            id=application.id.hex,
            region=application.region,
            name=application.name,
            code=application.code,
            logo_url=application.get_logo_url(),
            has_deployed=application.has_deployed,
            creator=creator,
            created=application.created,
            updated=application.updated,
            tag_info=tag_info,
        )

    def get_application(self) -> Application:
        """Return bound application object"""
        return self._application

    def get_profile(self) -> BkPluginProfile:
        """Return bound profile object"""
        return self._application.bk_plugin_profile


def make_bk_plugins(applications: Iterator[Application]) -> List[BkPlugin]:
    """Make a list of bk_plugin objects at once"""
    return [BkPlugin.from_application(app) for app in applications]


class DeployedStatus(BaseModel):
    """A helper class for storing deployed status"""

    deployed: bool
    addresses: List[Dict]


class DeployedStatusNoAddresses(BaseModel):
    """Similar to `DeployedStatus`, but have no `addresses`"""

    deployed: bool


DeployedStatuses = Mapping[str, Union[DeployedStatus, DeployedStatusNoAddresses]]


def get_deployed_statuses(bk_plugin: BkPlugin) -> DeployedStatuses:
    """Get the deployed statuses of a bk_plugin, result include both `deployed` and `addresses` fields
    for each environments.
    """
    module = bk_plugin.get_application().default_module
    result = {}
    for env in module.get_envs():
        deployed = env_is_deployed(env)
        if deployed:
            # Transform dataclass to raw dict for convenience, ignore empty address also
            addrs = [asdict(obj) for obj in ModuleEnvAvailableAddressHelper(env).addresses if obj.address]
        else:
            addrs = []
        result[env.environment] = DeployedStatus(deployed=deployed, addresses=addrs)
    return result


def get_deployed_statuses_without_addresses(bk_plugin: BkPlugin) -> DeployedStatuses:
    """Get the deployed statuses of given bk_plugin, result include only `deployed` field."""
    module = bk_plugin.get_application().default_module
    result: Dict[str, DeployedStatusNoAddresses] = {
        env.environment: DeployedStatusNoAddresses(deployed=env_is_deployed(env)) for env in module.get_envs()
    }
    return result


class BkPluginAppQuerySet:
    """QuerySet manager for bk_plugin related `Application`s"""

    def all(self) -> QuerySet:
        """Return all bk_plugin typed applications queryset"""
        return Application.objects.filter(is_plugin_app=True).only_active()

    def filter(
        self,
        search_term: str,
        order_by: List[str],
        tenant_id: str,
        has_deployed: Optional[bool] = None,
        distributor_code_name: Optional[str] = None,
        tag_id: Optional[int] = None,
    ) -> QuerySet:
        """filter queryset by given term

        :param has_deployed: If given, only return applications whose `has_deployed` property matches
        :param distributor_code_name: If given, only return results which have granted permissions to distributor
        """
        applications = Application.objects.filter(is_plugin_app=True, tenant_id=tenant_id)
        # Reuse the original application filter
        # Use `prefetch_related` to reduce database queries
        applications = (
            BaseApplicationFilter()
            .filter_queryset(applications, search_term=search_term, has_deployed=has_deployed, order_by=order_by)
            .prefetch_related("bk_plugin_profile")
        )
        if distributor_code_name:
            applications = applications.filter(distributors__code_name=distributor_code_name)
        if tag_id:
            # tag_id 的值为未分类时，过滤所有没有分类信息的插件
            tag_id = None if tag_id == PluginTagIdType.UNTAGGED.value else tag_id
            applications = applications.filter(bk_plugin_profile__tag=tag_id)
        return applications


def is_bk_plugin(application: Application) -> bool:
    """Check if an application is a plugin"""
    return application.is_plugin_app


def make_bk_plugin(application: Application) -> BkPlugin:
    """Make a bk_plugin object by given application

    :return: a `BkPlugin` object
    :raise TypeError: when application's "type" is wrong
    """
    if not is_bk_plugin(application):
        raise TypeError(f'application {application.code} is not "bk_plugin"')
    return BkPlugin.from_application(application)


class BkPluginDetailedGroup(BaseModel):
    """A grouped data type, includes a `BkPlugin` and other related fields, such as `profile` and
    `deploy_statuses`
    """

    plugin: BkPlugin
    deployed_statuses: DeployedStatuses
    profile: BkPluginProfile

    class Config:
        arbitrary_types_allowed = True


def plugin_to_detailed(plugin: BkPlugin, include_addresses: bool = True) -> BkPluginDetailedGroup:
    """Turn a simple `BkPlugin` object into another object with more details

    :param include_addresses: include "addresses" in result's `deployed_statuses` field or not
    """
    if include_addresses:
        deployed_statuses = get_deployed_statuses(plugin)
    else:
        deployed_statuses = get_deployed_statuses_without_addresses(plugin)

    return BkPluginDetailedGroup(
        plugin=plugin,
        deployed_statuses=deployed_statuses,
        profile=plugin.get_profile(),
    )
