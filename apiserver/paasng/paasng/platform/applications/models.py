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
import os
import time
import uuid
from typing import TYPE_CHECKING, Dict, List, Optional, Set, Union

from bkstorages.backends.bkrepo import RequestError
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, SuspiciousOperation
from django.db import models
from django.db.models import Q, QuerySet
from pilkit.processors import ResizeToFill

from paasng.core.core.storages.object_storage import app_logo_storage
from paasng.core.core.storages.redisdb import get_default_redis
from paasng.core.region.models import get_region
from paasng.core.tenant.constants import AppTenantMode
from paasng.core.tenant.fields import tenant_id_field_factory
from paasng.core.tenant.user import DEFAULT_TENANT_ID, get_tenant
from paasng.infras.iam.permissions.resources.application import ApplicationPermission
from paasng.platform.applications.constants import AppFeatureFlag, ApplicationRole, ApplicationType
from paasng.platform.applications.entities import SMartAppArtifactMetadata
from paasng.platform.modules.constants import SourceOrigin
from paasng.platform.modules.models.module import Module
from paasng.utils.basic import get_username_by_bkpaas_user_id
from paasng.utils.models import (
    BkUserField,
    OrderByField,
    OwnerTimestampedModel,
    ProcessedImageField,
    TimestampedModel,
    WithOwnerManager,
    make_json_field,
)

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from paasng.platform.sourcectl.models import RepositoryInstance

LOGO_SIZE = (144, 144)


class ApplicationQuerySet(models.QuerySet):
    """QuerySet for Applications"""

    @staticmethod
    def get_user_id(user):
        if hasattr(user, "pk"):
            return user.pk
        return user

    @staticmethod
    def get_username(user):
        """
        获取用户名称

        :param user:  User Object or user_id
        """
        if hasattr(user, "username"):
            return user.username

        return get_username_by_bkpaas_user_id(user)

    def _filter_by_user(self, user, tenant_id: str):
        """Filter applications, take application only if user play a role in it.

        :param user: User object or user_id
        :param tenant_id: the user's tenant ID
        """
        username = self.get_username(user)
        filters = ApplicationPermission().gen_user_app_filters(username, tenant_id)
        if not filters:
            return self.none()

        return self.filter(filters)

    def search_by_code_or_name(self, search_term):
        return self.filter(
            Q(code__icontains=search_term) | Q(name_en__icontains=search_term) | Q(name__icontains=search_term)
        )

    def only_active(self):
        return self.filter(is_active=True)

    def filter_by_regions(self, regions):
        return self.filter(region__in=regions)

    def filter_by_languages(self, languages):
        """Filter applications which have at least one module with given languages"""
        # return self.filter(language__in=languages)
        from paasng.platform.modules.models import Module

        ids = Module.objects.filter(application__in=self, language__in=languages).values_list(
            "application_id", flat=True
        )
        # Generate a new QuerySet object
        return self.model.objects.filter(id__in=ids)

    def filter_by_user(self, user, tenant_id: str, exclude_collaborated=False):
        qs = self._filter_by_user(user, tenant_id)
        if exclude_collaborated:
            qs = qs.filter(owner=self.get_user_id(user))
        return qs

    def filter_by_source_origin(self, source_origin: SourceOrigin) -> QuerySet:
        """Filter applications which have at least one module with given source origin"""
        from paasng.platform.modules.models import Module

        ids = Module.objects.filter(application__in=self, source_origin=source_origin).values_list(
            "application_id", flat=True
        )
        # Generate a new QuerySet object
        return self.model.objects.filter(id__in=ids)


class ApplicationManager(models.Manager):
    """Manager for Applications"""

    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class BaseApplicationFilter:
    """Base Application Filter"""

    @classmethod
    def filter_queryset(  # noqa: C901
        cls,
        queryset: QuerySet,
        is_active=None,
        regions=None,
        languages=None,
        search_term="",
        has_deployed: Optional[bool] = None,
        source_origin: Optional[SourceOrigin] = None,
        type_: Optional[ApplicationType] = None,
        order_by: Optional[List] = None,
        app_tenant_mode: Optional[str] = None,
        market_enabled: Optional[bool] = None,
    ):
        """Filter applications by given parameters"""
        if order_by is None:
            order_by = []
        if queryset.model is not Application:
            raise ValueError("BaseApplicationFilter only support to filter Application")

        if regions:
            queryset = queryset.filter_by_regions(regions)
        if languages:
            queryset = queryset.filter_by_languages(languages)
        if search_term:
            queryset = queryset.search_by_code_or_name(search_term)
        if has_deployed is not None:
            # When application has been deployed, it's `last_deployed_date` will not be empty.
            queryset = queryset.filter(last_deployed_date__isnull=not has_deployed)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active)
        if order_by:
            queryset = cls.process_order_by(order_by, queryset)
        if source_origin:
            queryset = queryset.filter_by_source_origin(source_origin)
        if market_enabled is not None:
            queryset = queryset.filter(market_config__enabled=market_enabled)
        if type_ is not None:
            queryset = queryset.filter(type=type_)
        if app_tenant_mode:
            queryset = queryset.filter(app_tenant_mode=app_tenant_mode)
        return queryset

    @staticmethod
    def process_order_by(order_by: List[str], queryset: QuerySet) -> QuerySet:
        """Process order_by fields"""
        fields = []
        for field in order_by:
            f = OrderByField.from_string(field)
            # If order_by field is "latest_operated_at", replace it with original field which has
            # related_name prefix.
            if f.name == "latest_operated_at":
                f.name = "latest_op_record__latest_operated_at"
                queryset = queryset.select_related("latest_op_record")
                fields.append(str(f))
                continue

            fields.append(field)
        return queryset.order_by(*fields)


class JustLeaveAppManager:
    """
    刚退出的应用管理器

    Q：为什么需要有这个管理器
    A：开发者中心接入权限中心后，由于接入的是 RBAC 模型，导致有这么一个链路
         用户退出权限中心用户组  ----异步任务----> 回收用户权限
      这样会出现一个问题：用户退出应用后，短时间（30s）内还有这个应用的权限，体验不佳
      这里的思路是：利用 Redis，缓存用户退出的应用 Code（5min），这段时间内，把这个应用 exclude 掉

    Q：为什么所有方法都加 try-except
    A：这个 manager 只是优化体验，如果 redis 挂了（虽然概率不大），也不该阻塞主流程
    """

    def __init__(self, username: str):
        self.redis_db = get_default_redis()
        self.username = username
        self.cache_key = f"bkpaas_just_leave_app_codes:{username}"

    def add(self, app_code: str) -> None:
        try:
            self.redis_db.rpush(self.cache_key, app_code)
            self.redis_db.expire(self.cache_key, settings.IAM_PERM_EFFECTIVE_TIMEDELTA)
        except Exception:
            pass

    def list(self) -> Set[str]:
        try:
            return {x.decode() for x in self.redis_db.lrange(self.cache_key, 0, -1)}
        except Exception:
            return set()


class UserApplicationFilter:
    """List user applications"""

    def __init__(self, user):
        self.user = user

    def filter(
        self,
        exclude_collaborated=False,
        is_active=None,
        regions=None,
        languages=None,
        search_term="",
        source_origin: Optional[SourceOrigin] = None,
        type_: Optional[ApplicationType] = None,
        order_by: Optional[List] = None,
        app_tenant_mode: Optional[str] = None,
    ):
        """Filter applications by given parameters"""
        if order_by is None:
            order_by = []
        applications = Application.objects.filter_by_user(
            self.user.pk, tenant_id=get_tenant(self.user).id, exclude_collaborated=exclude_collaborated
        )

        # 从缓存拿刚刚退出的应用 code exclude 掉，避免出现退出用户组，权限中心权限未同步的情况
        mgr = JustLeaveAppManager(get_username_by_bkpaas_user_id(self.user.pk))
        if just_leave_app_codes := mgr.list():
            applications = applications.exclude(code__in=just_leave_app_codes)

        return BaseApplicationFilter.filter_queryset(
            applications,
            is_active=is_active,
            regions=regions,
            languages=languages,
            search_term=search_term,
            source_origin=source_origin,
            order_by=order_by,
            type_=type_,
            app_tenant_mode=app_tenant_mode,
        )


def rename_logo_with_extra_prefix(instance: "Application", filename: str) -> str:
    """Generate uploaded logo filename with extra prefix"""
    dirname = os.path.dirname(filename)
    ext = os.path.splitext(filename)[-1]
    name = "{code}_{ts}{ext}".format(code=instance.code, ts=int(time.time()), ext=ext)
    return os.path.join(dirname, name)


class Application(OwnerTimestampedModel):
    """蓝鲸应用"""

    id = models.UUIDField("UUID", default=uuid.uuid4, primary_key=True, editable=False, auto_created=True, unique=True)
    code = models.CharField(verbose_name="应用代号", max_length=20, unique=True)
    name = models.CharField(verbose_name="应用名称", max_length=20)
    name_en = models.CharField(verbose_name="应用名称(英文)", max_length=20, help_text="目前仅用于 S-Mart 应用")

    # app_tenant_mode 和 app_tenant_id 字段共同控制了应用的“可用范围”，可能的组合包括：
    #
    # - app_tenant_mode: "global", app_tenant_id: ""，表示应用在全租户范围内可用。
    # - app_tenant_mode: "single", app_tenant_id: "foo"，表示应用仅在 foo 租户范围内可用。
    #
    # 应用的“可用范围”将影响对应租户的用户是否可在桌面上看到此应用，以及是否能通过应用链接访问
    # 应用（不在“可用范围”内的用户请求将被拦截）。
    #
    # ## app_tenant_id 和 tenant_id 字段的区别
    #
    # 虽然这两个字段都存储“租户”，且值可能相同，但二者有本质区别。tenant_id 是系统级字段，值
    # 总是等于当前这条数据的所属租户，它确定了数据的所有权。而 app_tenant_id 是业务功能层面的
    # 字段，它和 app_tenant_mode 共同控制前面提到的业务功能——应用“可用范围”。
    #
    app_tenant_mode = models.CharField(
        verbose_name="应用租户模式",
        max_length=16,
        default=AppTenantMode.SINGLE.value,
        help_text="应用在租户层面的可用范围，可选值：全租户、指定租户",
    )
    app_tenant_id = models.CharField(
        verbose_name="应用租户 ID",
        max_length=32,
        default=DEFAULT_TENANT_ID,
        help_text="应用对哪个租户的用户可用，当应用租户模式为全租户时，本字段值为空",
    )
    type = models.CharField(
        verbose_name="应用类型",
        max_length=16,
        default=ApplicationType.DEFAULT.value,
        db_index=True,
        help_text="与应用部署方式相关的类型信息",
    )
    is_smart_app = models.BooleanField(verbose_name="是否为 S-Mart 应用", default=False)
    is_plugin_app = models.BooleanField(
        verbose_name="是否为插件应用",
        default=False,
        help_text="蓝鲸应用插件：供标准运维、ITSM 等 SaaS 使用，有特殊逻辑",
    )
    is_ai_agent_app = models.BooleanField(
        verbose_name="是否为 AI Agent 插件应用",
        default=False,
    )
    language = models.CharField(verbose_name="编程语言", max_length=32)

    creator = BkUserField()
    is_active = models.BooleanField(verbose_name="是否活跃", default=True)
    is_deleted = models.BooleanField("是否删除", default=False)
    last_deployed_date = models.DateTimeField(verbose_name="最近部署时间", null=True)  # 范围：应用下所有模块的所有环境

    logo = ProcessedImageField(
        verbose_name="应用 Logo 图片",
        storage=app_logo_storage,
        upload_to=rename_logo_with_extra_prefix,
        processors=[ResizeToFill(*LOGO_SIZE)],
        format="PNG",
        options={"quality": 95},
        null=True,
    )
    tenant_id = tenant_id_field_factory()

    objects: ApplicationQuerySet = ApplicationManager.from_queryset(ApplicationQuerySet)()
    default_objects = models.Manager()

    class Meta:
        # 应用名称租户内唯一
        unique_together = ("app_tenant_id", "name")

    @property
    def has_deployed(self) -> bool:
        """If current application has been SUCCESSFULLY deployed"""
        return bool(self.last_deployed_date)

    @property
    def config_info(self) -> Dict:
        """获取应用配置信息

        NOTE: This property was named "config_info" in purpose of backward-compatibility, what
        it truly does is return Application's specifications.
        """
        from .specs import AppSpecs

        return AppSpecs(self).to_dict()

    @property
    def engine_enabled(self) -> bool:
        """获取是否开启引擎（即判断是否“精简版应用”）"""
        from .specs import AppSpecs

        return AppSpecs(self).engine_enabled

    def get_source_obj(self) -> "RepositoryInstance":
        """获取 Application 对应的源码 Repo 对象"""
        return self.get_default_module().get_source_obj()

    def get_engine_app(self, environment: str, module_name=None):
        """Get the engine app of current application"""
        module = self.get_module(module_name=module_name)
        engine_app = module.get_envs(environment=environment).engine_app
        return engine_app

    def get_module_with_lock(self, module_name: str):
        """获取模块并且添加行锁，仅能在 transaction 中生效"""
        if not module_name:
            return self.get_default_module_with_lock()
        return self.modules.select_for_update().get(name=module_name)

    def get_default_module_with_lock(self):
        """获取主模块并且添加行锁，仅能在 transaction 中生效"""
        return self.modules.select_for_update().get(is_default=True)

    @property
    def default_module(self):
        """A shortcut property for getting default module"""
        return self.get_default_module()

    def get_default_module(self):
        return self.modules.get(is_default=True)

    def get_module(self, module_name: Optional[str]):
        """Get a module object by given module_name."""
        if not module_name:
            return self.get_default_module()
        return self.modules.get(name=module_name)

    def get_app_envs(self, environment=None):
        """获取所有环境对象(所有模块)"""
        if environment:
            return self.envs.get(environment=environment)
        return self.envs.all()

    def get_product(self):
        try:
            return getattr(self, "product", None)
        except ObjectDoesNotExist:
            return None

    def get_administrators(self):
        """获取具有管理权限的人员名单"""
        from paasng.infras.iam.helpers import fetch_role_members

        return fetch_role_members(self.code, ApplicationRole.ADMINISTRATOR)

    def get_devopses(self) -> List[str]:
        """获取具有运营权限的人员名单"""
        from paasng.infras.iam.helpers import fetch_role_members

        devopses = fetch_role_members(self.code, ApplicationRole.OPERATOR) + fetch_role_members(
            self.code, ApplicationRole.ADMINISTRATOR
        )
        return list(set(devopses))

    def get_developers(self) -> List[str]:
        """获取具有开发权限的人员名单"""
        from paasng.infras.iam.helpers import fetch_role_members

        developers = fetch_role_members(self.code, ApplicationRole.DEVELOPER) + fetch_role_members(
            self.code, ApplicationRole.ADMINISTRATOR
        )
        return list(set(developers))

    def has_customized_logo(self) -> bool:
        """Check if application has uploaded a customized logo"""
        return self.logo and self.logo.name

    def get_logo_url(self) -> str:
        """获取应用 Logo 图片地址，未设置时返回默认 Logo"""
        default_url = settings.APPLICATION_DEFAULT_LOGO
        # 插件应用使用独立的 Logo 以作区分
        if self.is_plugin_app:
            default_url = settings.PLUGIN_APP_DEFAULT_LOGO

        if self.logo:
            try:
                return self.logo.url
            except (SuspiciousOperation, RequestError):
                # 在有问题的测试环境下，个别应用的 logo 地址可能会无法生成
                logger.info("Unable to make logo url for application: %s", self.code)
                return default_url
        return default_url

    def delete(self, *args, **kwargs):
        # 软删除时不会删除数据, 而是通过标记删除字段 is_deleted 来软删除
        self.is_deleted = True
        self.save(update_fields=["is_deleted", "updated"])

    def hard_delete(self, *args, **kwargs):
        # 硬删除时直接删除表中数据
        super().delete(*args, **kwargs)

    def __str__(self):
        return "{name}[{code}]".format(name=self.name, code=self.code)


class ApplicationMembership(TimestampedModel):
    """[deprecated] 切换为权限中心用户组存储用户信息

    Members for one application
    """

    user = BkUserField()
    application = models.ForeignKey(Application, on_delete=models.CASCADE)
    role = models.IntegerField(default=ApplicationRole.DEVELOPER.value)

    class Meta:
        unique_together = ("user", "application", "role")

    def __str__(self):
        return "{app_code}-{user}-{role}".format(
            app_code=self.application.code, user=self.user, role=ApplicationRole.get_choice_label(self.role)
        )


class ApplicationEnvironment(TimestampedModel):
    """记录蓝鲸应用在不同部署环境下对应的 Engine App"""

    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name="envs")
    module = models.ForeignKey("modules.Module", on_delete=models.CASCADE, related_name="envs", null=True)
    engine_app = models.OneToOneField("engine.EngineApp", on_delete=models.CASCADE, related_name="env")
    environment = models.CharField(verbose_name="部署环境", max_length=16)
    is_offlined = models.BooleanField(default=False, help_text="是否已经下线，仅成功下线后变为False")

    tenant_id = tenant_id_field_factory()

    class Meta:
        unique_together = ("module", "environment")

    def __str__(self):
        return "{app_code}-{env}".format(app_code=self.application.code, env=self.environment)

    def get_engine_app(self):
        return self.engine_app

    @property
    def wl_app(self):
        """Return the WlApp object(in 'workloads' module)"""
        return self.engine_app.to_wl_obj()

    def is_production(self) -> bool:
        """判断当前环境是否用于生产"""
        return self.environment == "prod"

    def is_running(self) -> bool:
        """Check if current environment is up and running"""
        # TODO: Replace with env_is_running
        from paasng.platform.engine.models import Deployment

        if self.is_offlined:
            return False

        # Check if latest deployment has been succeeded
        try:
            Deployment.objects.filter_by_env(self).latest_succeeded()
        except Deployment.DoesNotExist:
            return False
        else:
            return True

    def restore_archived(self):
        """Restore the environment from "archived" status."""
        self.is_offlined = False
        self.save(update_fields=["is_offlined"])


# Create an alias name to reduce misunderstandings
ModuleEnvironment = ApplicationEnvironment


def get_default_feature_flags(application: "Application") -> Dict[str, bool]:
    """get default_feature_flags mapping for an application

    default features are controlled by different region or type of the application
    """
    # 从常量表获取默认值 default_feature_flag(几乎都是 disable)
    default_feature_flags = AppFeatureFlag.get_default_flags()

    # 从 region 配置获取该 region 开启的 FeatureFlag
    region = get_region(application.region)
    enabled_feature_set = set(region.enabled_feature_flags)
    for flag_name, _ in AppFeatureFlag.get_django_choices():
        if flag_name in enabled_feature_set:
            default_feature_flags[flag_name] = True

    # reset default_feature_flag by application type
    if not application.engine_enabled:
        default_feature_flags[AppFeatureFlag.PA_INGRESS_ANALYTICS] = False
    return default_feature_flags


class ApplicationFeatureFlagManager(models.Manager):
    """所有方法均同时兼容两种调用方式:

    - 通过外键对象查询, 例如 application.feature_flag.get_application_features()
    - 通过 objects 对象查询, 例如 ApplicationFeatureFlag.objects.get_application_features(application)
    """

    def get_application_features(self, application: Optional[Application] = None) -> Dict[str, bool]:
        """返回应用生效的标志"""
        instance, qs = self._build_queryset(application)

        feature_flag = get_default_feature_flags(instance)
        for feature in qs.all():
            feature_flag[feature.name] = feature.effect
        return feature_flag

    def set_feature(self, key: Union[str, AppFeatureFlag], value: bool, application: Optional[Application] = None):
        """设置 feature 状态"""
        instance, qs = self._build_queryset(application)
        return qs.update_or_create(
            application=instance, name=AppFeatureFlag(key), defaults={"effect": value, "tenant_id": instance.tenant_id}
        )

    def has_feature(self, key: Union[str, AppFeatureFlag], application: Optional[Application] = None) -> bool:
        """判断app是否具有feature,如果查数据库无记录，则返回默认值"""
        name = AppFeatureFlag(key)
        instance, qs = self._build_queryset(application)

        try:
            effect = qs.get(name=name).effect
        except ApplicationFeatureFlag.DoesNotExist:
            effect = get_default_feature_flags(instance)[name]
        return effect

    def _build_queryset(self, application: Optional[Application] = None):
        """处理 QuerySet 与 Application 对象."""
        qs = self.get_queryset()
        if not hasattr(self, "instance"):
            qs = qs.filter(application=application)
        else:
            application = self.instance

        if not isinstance(application, Application):
            raise TypeError(f"params<{application}> is not an Application")

        return application, qs


class ApplicationFeatureFlag(TimestampedModel):
    """
    移动端、应用市场白名单等app特性标记
    """

    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name="feature_flag")
    effect = models.BooleanField("是否允许(value)", default=True)
    name = models.CharField("特性名称(key)", max_length=30)

    tenant_id = tenant_id_field_factory()

    objects = ApplicationFeatureFlagManager()


class UserMarkedApplication(OwnerTimestampedModel):
    application = models.ForeignKey(Application, on_delete=models.CASCADE)
    objects = WithOwnerManager()

    tenant_id = tenant_id_field_factory()

    class Meta:
        unique_together = ("application", "owner")

    def __str__(self):
        return self.code

    @property
    def code(self):
        return self.application.code


class ApplicationDeploymentModuleOrder(models.Model):
    user = BkUserField()
    module = models.ForeignKey(Module, on_delete=models.CASCADE, verbose_name="模块", db_constraint=False)
    order = models.IntegerField(verbose_name="顺序")

    tenant_id = tenant_id_field_factory()

    class Meta:
        verbose_name = "模块顺序"
        unique_together = ("user", "module")


SMartAppArtifactMetadataField = make_json_field("SMartAppArtifactMetadataField", SMartAppArtifactMetadata)


class SMartAppExtraInfo(models.Model):
    """SMart 应用额外信息"""

    app = models.OneToOneField(Application, on_delete=models.CASCADE, db_constraint=False)
    original_code = models.CharField(verbose_name="描述文件中的应用原始 code", max_length=20)

    artifact_metadata = SMartAppArtifactMetadataField(
        default=SMartAppArtifactMetadata, help_text="smart app 的制品元数据"
    )

    tenant_id = tenant_id_field_factory()

    @property
    def use_cnb(self) -> bool:
        return self.artifact_metadata.use_cnb

    def set_use_cnb_flag(self, use_cnb: bool):
        self.artifact_metadata.use_cnb = use_cnb
        self.save(update_fields=["artifact_metadata"])

    def get_proc_entrypoints(self, module_name: str) -> dict[str, list[str]] | None:
        """根据模块名, 获取模块下所有进程的 entrypoints

        :param module_name: 模块名
        :return proc_entrypoints, 格式如 {进程名: entrypoint}
        """
        return self.artifact_metadata.module_proc_entrypoints.get(module_name)

    def set_proc_entrypoints(self, module_name: str, proc_entrypoints: dict[str, list[str]]):
        """设置模块下进程的 entrypoints

        :param module_name: 模块名
        :param proc_entrypoints: 进程 entrypoints
        """
        self.artifact_metadata.module_proc_entrypoints[module_name] = proc_entrypoints
        self.save(update_fields=["artifact_metadata"])

    def get_image_tar(self, module_name: str) -> str | None:
        """获取模块使用的镜像 tar 包名

        :param module_name: 模块名
        :return 模块使用的镜像 tar 包名. 如果 artifact_metadata 中没有, 则返回默认值"模块名.tgz"
        """
        return self.artifact_metadata.module_image_tars.get(module_name, f"{module_name}.tgz")

    def set_image_tar(self, module_name: str, image_tar: str):
        """设置模块使用的镜像 tar 包名

        :param module_name: 模块名
        :param image_tar: 镜像 tar 包名
        """
        self.artifact_metadata.module_image_tars[module_name] = image_tar
        self.save(update_fields=["artifact_metadata"])
