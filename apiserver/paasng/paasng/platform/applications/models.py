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
import os
import time
import uuid
from typing import TYPE_CHECKING, Dict, List, Optional, Union

from bkstorages.backends.bkrepo import RequestError
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, SuspiciousOperation
from django.db import models
from django.db.models import Q, QuerySet
from django.shortcuts import get_object_or_404
from pilkit.processors import ResizeToFill

from paasng.accessories.iam.helpers import fetch_role_members
from paasng.accessories.iam.permissions.resources.application import ApplicationPermission
from paasng.platform.applications.constants import AppFeatureFlag, ApplicationRole, ApplicationType
from paasng.platform.core.storages.object_storage import app_logo_storage
from paasng.platform.modules.constants import SourceOrigin
from paasng.platform.region.models import get_region
from paasng.utils.basic import get_username_by_bkpaas_user_id
from paasng.utils.models import (
    BkUserField,
    OrderByField,
    OwnerTimestampedModel,
    ProcessedImageField,
    TimestampedModel,
    WithOwnerManager,
)

logger = logging.getLogger(__name__)


if TYPE_CHECKING:
    from paasng.dev_resources.sourcectl.models import RepositoryInstance


LOGO_SIZE = (144, 144)


class ApplicationQuerySet(models.QuerySet):
    """QuerySet for Applications"""

    @staticmethod
    def get_user_id(user):
        if hasattr(user, 'pk'):
            return user.pk
        return user

    @staticmethod
    def get_username(user):
        """
        获取用户名称

        :param user:  User Object or user_id
        """
        if hasattr(user, 'username'):
            return user.username

        return get_username_by_bkpaas_user_id(user)

    def _filter_by_user(self, user):
        """Filter applications, take application only if user play a role in it.

        :param user: User object or user_id
        """
        username = self.get_username(user)
        filters = ApplicationPermission().gen_user_app_filters(username)
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

    def filter_by_user(self, user, exclude_collaborated=False):
        qs = self._filter_by_user(user)
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
    def filter_queryset(
        cls,
        queryset: QuerySet,
        include_inactive=False,
        regions=None,
        languages=None,
        search_term='',
        has_deployed: Optional[bool] = None,
        source_origin: Optional[SourceOrigin] = None,
        type_: Optional[ApplicationType] = None,
        order_by: Optional[List] = None,
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
        if not include_inactive:
            queryset = queryset.only_active()
        if order_by:
            queryset = cls.process_order_by(order_by, queryset)
        if source_origin:
            queryset = queryset.filter_by_source_origin(source_origin)
        if market_enabled is not None:
            queryset = queryset.filter(market_config__enabled=market_enabled)
        if type_ is not None:
            queryset = queryset.filter(type=type_)
        return queryset

    @staticmethod
    def process_order_by(order_by: List[str], queryset: QuerySet) -> QuerySet:
        """Process order_by fields"""
        fields = []
        for field in order_by:
            f = OrderByField.from_string(field)
            # If order_by field is "latest_operated_at", replace it with original field which has
            # related_name prefix.
            if f.name == 'latest_operated_at':
                f.name = 'latest_op__latest_operated_at'
                queryset = queryset.select_related('latest_op')
                field = str(f)

            fields.append(field)
        return queryset.order_by(*fields)


class UserApplicationFilter:
    """List user applications"""

    def __init__(self, user):
        self.user = user

    def filter(
        self,
        exclude_collaborated=False,
        include_inactive=False,
        regions=None,
        languages=None,
        search_term='',
        source_origin: Optional[SourceOrigin] = None,
        type_: Optional[ApplicationType] = None,
        order_by: Optional[List] = None,
    ):
        """Filter applications by given parameters"""
        if order_by is None:
            order_by = []
        applications = Application.objects.filter_by_user(self.user.pk, exclude_collaborated=exclude_collaborated)
        return BaseApplicationFilter.filter_queryset(
            applications,
            include_inactive=include_inactive,
            regions=regions,
            languages=languages,
            search_term=search_term,
            source_origin=source_origin,
            order_by=order_by,
            type_=type_,
        )


def rename_logo_with_extra_prefix(instance: 'Application', filename: str) -> str:
    """Generate uploaded logo filename with extra prefix"""
    dirname = os.path.dirname(filename)
    ext = os.path.splitext(filename)[-1]
    name = "{code}_{ts}{ext}".format(code=instance.code, ts=int(time.time()), ext=ext)
    return os.path.join(dirname, name)


class Application(OwnerTimestampedModel):
    """蓝鲸应用"""

    id = models.UUIDField('UUID', default=uuid.uuid4, primary_key=True, editable=False, auto_created=True, unique=True)
    code = models.CharField(verbose_name='应用代号', max_length=20, unique=True)
    name = models.CharField(verbose_name='应用名称', max_length=20, unique=True)
    name_en = models.CharField(verbose_name='应用名称(英文)', max_length=20, help_text="目前仅用于 S-Mart 应用")

    type = models.CharField(verbose_name='应用类型', max_length=16, default=ApplicationType.DEFAULT.value, db_index=True)
    is_smart_app = models.BooleanField(verbose_name='是否为 S-Mart 应用', default=False)
    is_scene_app = models.BooleanField(verbose_name='是否为场景 SaaS 应用', default=False)
    language = models.CharField(verbose_name='编程语言', max_length=32)

    creator = BkUserField()
    is_active = models.BooleanField(verbose_name='是否活跃', default=True)
    is_deleted = models.BooleanField('是否删除', default=False)
    last_deployed_date = models.DateTimeField(verbose_name='最近部署时间', null=True)  # 范围：应用下所有模块的所有环境

    logo = ProcessedImageField(
        verbose_name='应用 Logo 图片',
        storage=app_logo_storage,
        upload_to=rename_logo_with_extra_prefix,
        processors=[ResizeToFill(*LOGO_SIZE)],
        format='PNG',
        options={'quality': 95},
        null=True,
    )

    objects: ApplicationQuerySet = ApplicationManager.from_queryset(ApplicationQuerySet)()
    default_objects = models.Manager()

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

    @property
    def market_published(self) -> bool:
        """应用是否已发布到应用市场"""
        from paasng.publish.market.models import MarketConfig

        market_config, _ = MarketConfig.objects.get_or_create_by_app(self)
        return market_config.enabled

    def get_source_obj(self) -> 'RepositoryInstance':
        """获取 Application 对应的源码 Repo 对象"""
        return self.get_default_module().get_source_obj()

    def get_engine_app(self, environment, module_name=None):
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
        """Get a module object by given module_name"""
        if not module_name:
            return self.get_default_module()
        return get_object_or_404(self.modules, name=module_name)

    def get_app_envs(self, environment=None):
        """获取所有环境对象(所有模块)"""
        if environment:
            return self.envs.get(environment=environment)
        return self.envs.all()

    def get_deploy_info(self):
        """检测应用的部署状态"""
        # TODO: remove this method and move "exposed_links" property out of application
        return get_exposed_links(self)

    def get_product(self):
        try:
            return getattr(self, "product", None)
        except ObjectDoesNotExist:
            return None

    def get_administrators(self):
        """获取具有管理权限的人员名单"""
        return fetch_role_members(self.code, ApplicationRole.ADMINISTRATOR)

    def get_devopses(self) -> List[str]:
        """获取具有运营权限的人员名单"""
        devopses = fetch_role_members(self.code, ApplicationRole.OPERATOR) + fetch_role_members(
            self.code, ApplicationRole.ADMINISTRATOR
        )
        return list(set(devopses))

    def get_developers(self) -> List[str]:
        """获取具有开发权限的人员名单"""
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
        if self.type == ApplicationType.BK_PLUGIN.value:
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
        # 不会删除数据, 而是通过标记删除字段 is_deleted 来软删除
        self.is_deleted = True
        self.save()

    def __str__(self):
        return u'{name}[{code}]'.format(name=self.name, code=self.code)


class ApplicationMembership(TimestampedModel):
    """[deprecated] 切换为权限中心用户组存储用户信息

    Members for one application
    """

    user = BkUserField()
    application = models.ForeignKey(Application, on_delete=models.CASCADE)
    role = models.IntegerField(default=ApplicationRole.DEVELOPER.value)

    class Meta:
        unique_together = ('user', 'application', 'role')

    def __str__(self):
        return u"{app_code}-{user}-{role}".format(
            app_code=self.application.code, user=self.user, role=ApplicationRole.get_choice_label(self.role)
        )


class ApplicationEnvironment(TimestampedModel):
    """记录蓝鲸应用在不同部署环境下对应的 Engine App"""

    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name='envs')
    module = models.ForeignKey('modules.Module', on_delete=models.CASCADE, related_name='envs', null=True)
    engine_app = models.OneToOneField('engine.EngineApp', on_delete=models.CASCADE, related_name='env')
    environment = models.CharField(verbose_name=u'部署环境', max_length=16)
    is_offlined = models.BooleanField(default=False, help_text=u'是否已经下线，仅成功下线后变为False')

    class Meta:
        unique_together = ('module', 'environment')

    def __str__(self):
        return u"{app_code}-{env}".format(app_code=self.application.code, env=self.environment)

    def get_engine_app(self):
        return self.engine_app

    @property
    def wl_app(self):
        """Return the WlApp object(in 'workloads' module)"""
        return self.engine_app.to_wl_obj()

    def get_exposed_link(self):
        # TODO: move this method out of ApplicationEnvironment class
        from paasng.publish.entrance.exposer import get_exposed_url

        entrance = get_exposed_url(self)
        return entrance.address if entrance else None

    def is_production(self) -> bool:
        """判断当前环境是否用于生产"""
        return self.environment == 'prod'

    def is_running(self) -> bool:
        """Check if current environment is up and running"""
        # TODO: Replace with env_is_running
        from paasng.engine.models import Deployment

        if self.is_offlined:
            return False

        # Check if latest deployment has been succeed
        try:
            Deployment.objects.filter_by_env(self).latest_succeeded()
            return True
        except Deployment.DoesNotExist:
            return False


# Make an alias name to descrease misunderstanding
ModuleEnvironment = ApplicationEnvironment


def get_default_feature_flags(application: 'Application') -> Dict[str, bool]:
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
        return qs.update_or_create(application=instance, name=AppFeatureFlag(key), defaults={"effect": value})

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
        if self.instance is None:
            qs = qs.filter(application=application)

        if application is None:
            application = self.instance

        if not isinstance(application, Application):
            raise ValueError(f"params<{application}> is not an Application")

        return application, qs


class ApplicationFeatureFlag(TimestampedModel):
    """
    移动端、应用市场白名单等app特性标记
    """

    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name="feature_flag")
    effect = models.BooleanField(u"是否允许(value)", default=True)
    name = models.CharField(u"特性名称(key)", max_length=30)

    objects = ApplicationFeatureFlagManager()


def get_exposed_links(application: Application) -> Dict:
    """Return exposed links for default module"""
    from paasng.publish.entrance.exposer import get_module_exposed_links

    return get_module_exposed_links(application.get_default_module())


class UserMarkedApplication(OwnerTimestampedModel):
    application = models.ForeignKey(Application, on_delete=models.CASCADE)
    objects = WithOwnerManager()

    class Meta:
        unique_together = ("application", "owner")

    def __str__(self):
        return self.code

    @property
    def code(self):
        return self.application.code
