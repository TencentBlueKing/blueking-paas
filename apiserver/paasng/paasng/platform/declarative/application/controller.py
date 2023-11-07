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
"""Controller for declarative applications
"""


import logging
from typing import Dict, List, Optional

from django.db.transaction import atomic
from django.utils.translation import gettext_lazy as _

from paasng.accessories.publish.market.constant import AppType, ProductSourceUrlType
from paasng.accessories.publish.market.models import DisplayOptions, MarketConfig, Product
from paasng.accessories.publish.market.protections import ModulePublishPreparer
from paasng.accessories.publish.market.signals import product_create_or_update_by_operator
from paasng.accessories.servicehub.exceptions import ServiceObjNotFound
from paasng.accessories.servicehub.manager import mixed_service_mgr
from paasng.accessories.servicehub.sharing import ServiceSharingManager
from paasng.core.region.models import get_region
from paasng.infras.accounts.models import User, UserProfile
from paasng.infras.accounts.permissions.application import user_has_app_action_perm
from paasng.infras.iam.permissions.resources.application import AppAction
from paasng.infras.oauth2.utils import create_oauth2_client
from paasng.platform.applications.handlers import application_logo_updated
from paasng.platform.applications.models import Application
from paasng.platform.applications.signals import application_default_module_switch, post_create_application
from paasng.platform.declarative.application.constants import APP_CODE_FIELD
from paasng.platform.declarative.application.fields import AppNameField, AppRegionField
from paasng.platform.declarative.application.resources import ApplicationDesc, MarketDesc, ModuleDesc, ServiceSpec
from paasng.platform.declarative.application.serializers import AppDescriptionSLZ
from paasng.platform.declarative.basic import remove_omitted
from paasng.platform.declarative.exceptions import ControllerError, DescriptionValidationError
from paasng.platform.declarative.models import ApplicationDescription
from paasng.platform.modules.constants import SourceOrigin
from paasng.platform.modules.exceptions import ModuleInitializationError
from paasng.platform.modules.manager import Module, initialize_smart_module

logger = logging.getLogger(__name__)


class AppDeclarativeController:
    """A controller which creates or updates application declaratively.

    :param user: Performing actions as whom
    :param spec_version: Config schema version
    """

    # 默认是 Smart 应用，场景模板应用需要特殊指定
    source_origin = SourceOrigin.S_MART
    update_allowed_fields = [AppNameField, AppRegionField]

    def __init__(self, user: User, source_origin: Optional[SourceOrigin] = None):
        if source_origin:
            self.source_origin = source_origin
        self.user = user

    def perform_action(self, desc: ApplicationDesc) -> Application:
        if not desc.instance_existed:
            return self.perform_create(desc)
        else:
            return self.perform_update(desc)

    @atomic
    def perform_create(self, desc: ApplicationDesc) -> Application:
        """Create application by given input data"""
        allowed_regions = self.get_allowed_regions()
        if not desc.region:
            desc.region = allowed_regions[0]
        elif desc.region not in allowed_regions:
            raise DescriptionValidationError({'region': _('用户没有权限在 {} 下创建应用').format(desc.region)})

        is_smart_app = self.source_origin == SourceOrigin.S_MART
        is_scene_app = self.source_origin == SourceOrigin.SCENE

        application = Application.objects.create(
            owner=self.user.pk,
            creator=self.user.pk,
            region=desc.region,
            code=desc.code,
            name=desc.name_zh_cn,
            name_en=desc.name_en,
            is_smart_app=is_smart_app,
            is_scene_app=is_scene_app,
            # TODO: 是否要设置 language?
            language=desc.default_module.language.value,
        )
        create_oauth2_client(application.code, application.region)
        self.sync_modules(application, desc.modules)
        default_module = application.get_default_module()

        post_create_application.send(sender=self.__class__, application=application)

        # Create market related data after application created, to avoid market related data be covered
        MarketConfig.objects.create(
            region=application.region,
            application=application,
            enabled=False,
            auto_enable_when_deploy=True,
            source_module=default_module,
            source_url_type=ProductSourceUrlType.ENGINE_PROD_ENV.value,
            source_tp_url='',
        )

        self.sync_market_fields(application, desc.market)
        self.sync_services_fields(application, desc.modules)
        self.save_description(desc, application, is_creation=True)
        return application

    def get_allowed_regions(self) -> List[str]:
        """Return all allowed regions for current user"""
        user_profile = UserProfile.objects.get_profile(self.user)
        return [r.name for r in user_profile.enable_regions]

    @atomic
    def perform_update(self, desc: ApplicationDesc) -> Application:
        """Update application by given input data"""
        # Permission check
        application = Application.objects.get(code=desc.code)
        # Set region field if omitted
        if not desc.region:
            desc.region = application.region

        if not user_has_app_action_perm(self.user, application, AppAction.BASIC_DEVELOP):
            raise DescriptionValidationError({APP_CODE_FIELD: _('你没有权限操作当前应用')})

        # Handle field modifications
        for field_cls in self.update_allowed_fields:
            field_cls(application).handle_desc(desc)

        self.sync_modules(application, desc.modules)
        self.sync_market_fields(application, desc.market)
        self.sync_services_fields(application, desc.modules)
        self.save_description(desc, application, is_creation=False)
        return application

    def sync_modules(self, application: Application, modules_desc: Dict[str, ModuleDesc]):
        """Sync modules to database"""
        region = get_region(application.region)
        for module_name, module_desc in modules_desc.items():
            if application.modules.filter(name=module_name).exists():
                # 重新设置主模块
                logger.info('Module named "%s" already exists, skip create!', module_name)
                continue

            # Create module
            module = Module.objects.create(
                application=application,
                name=module_name,
                # NOTE: is_default 字段在 sync_default_module 函数中处理
                is_default=False,
                region=application.region,
                owner=application.owner,
                creator=application.creator,
                # Extra fields
                source_origin=self.source_origin.value,
                source_type=None,
                language=module_desc.language.value,
                source_init_template='',
                exposed_url_type=region.entrance_config.exposed_url_type,
            )
            # Initialize module
            try:
                initialize_smart_module(module)
            except ModuleInitializationError as e:
                raise ControllerError(str(e))

        self._sync_default_module(application, modules_desc)

    def _sync_default_module(self, application: Application, modules_desc: Dict[str, ModuleDesc]):
        """Switch Default Module if changed."""
        for module_name, module_desc in modules_desc.items():
            if module_desc.is_default:
                new_default_module_name = module_name
                break
        else:
            raise ControllerError(_("未定义主模块, 请检查 app_desc.yaml."))

        if not application.modules.filter(is_default=True).exists():
            # 应用未设置主模块(首次创建模块), 则进行设置
            application.modules.filter(name=new_default_module_name).update(is_default=True)
            return

        old_default_module = application.get_default_module_with_lock()
        if old_default_module.name == new_default_module_name:
            # 未切换主模块
            return

        new_default_module = application.get_module_with_lock(new_default_module_name)
        market_enabled = application.market_config.enabled
        if market_enabled and not ModulePublishPreparer(new_default_module).all_matched:
            raise ControllerError(
                _("目标 {new_default_module_name} 模块未满足应用市场服务开启条件，切换主模块会导致应用在市场中访问异常, 请关闭市场开关后重新操作。").format(
                    new_default_module_name=new_default_module_name
                )
            )

        logger.info(
            f'Switching default module for application[{application.code}], '
            f'{old_default_module.name} -> {new_default_module.name}...'
        )
        old_default_module.is_default = False
        new_default_module.is_default = True
        new_default_module.save(update_fields=["is_default", "updated"])
        old_default_module.save(update_fields=["is_default", "updated"])

        application_default_module_switch.send(
            sender=application, application=application, new_module=new_default_module, old_module=old_default_module
        )

    def sync_market_fields(self, application: Application, market_desc: Optional[MarketDesc]):
        """Sync market related fields to database"""
        if not market_desc:
            return

        # TODO Fields: logo / state
        product_defaults = remove_omitted(
            dict(
                code=application.code,
                name_zh_cn=application.name,
                name_en=application.name_en,
                type=AppType.PAAS_APP.value,
                description_en=market_desc.description_en,
                description_zh_cn=market_desc.description_zh_cn,
                introduction_en=market_desc.introduction_en,
                introduction_zh_cn=market_desc.introduction_zh_cn,
                logo=market_desc.logo,
            )
        )
        logo = product_defaults.pop("logo", None)
        if market_desc.tag_id:
            product_defaults['tag_id'] = market_desc.tag_id

        product, created = Product.objects.update_or_create(application=application, defaults=product_defaults)
        if logo:
            # Logo was now migrated to Application model
            # TODO: Refactor more to make this look more natural
            application.logo.save(logo.name, logo)
            # Send signal to trigger extra processes for logo
            application_logo_updated.send(sender=application, application=application)

        # Update display options
        try:
            display_options = market_desc.display_options.dict()
        except NotImplementedError:
            display_options = {}
        DisplayOptions.objects.update_or_create(product=product, defaults=display_options)

        # Send signal
        product_create_or_update_by_operator.send(
            sender=self.__class__, product=product, operator=self.user.pk, created=created
        )

    def sync_services_fields(self, application: Application, desc: Dict[str, ModuleDesc]):
        """Sync services related field for application"""
        dependency_tree: Dict[str, List[str]] = {}
        for module_name, module_desc in desc.items():
            dependency_tree[module_name] = []
            for service in module_desc.services:
                if service.shared_from:
                    dependency_tree[module_name].append(service.shared_from)

        # NOTE: 由 AppDescriptionSLZ 校验 shared_from 的模块是否存在, 这里不再重复校验
        for module_name in flatten_dependency_tree(dependency_tree):
            module = application.get_module(module_name)
            self._sync_module_services_fields(application, module, desc[module_name].services)

    def _sync_module_services_fields(self, application: Application, module: Module, services: List[ServiceSpec]):
        """Sync services related field for single module."""
        for service in services:
            try:
                obj = mixed_service_mgr.find_by_name(service.name, region=module.region)
            except ServiceObjNotFound:
                logger.warning('Skip binding, service called "%s" not found', service.name)
                continue

            if service.shared_from:
                manager = ServiceSharingManager(module)
                if manager.get_shared_info(service=obj):
                    logger.info('Skip, service "%s" already created shared attachment', obj.name)
                    continue

                ref_module = application.get_module(service.shared_from)
                manager.create(service=obj, ref_module=ref_module)
            else:
                if mixed_service_mgr.module_is_bound_with(obj, module):
                    logger.info('Skip, service "%s" already bound', obj.name)
                    continue

                logger.info('Bind service "%s" to Module "%s".', service.name, module)
                mixed_service_mgr.bind_service(obj, module, specs=service.specs)

    def save_description(self, desc: ApplicationDesc, application: Application, is_creation: bool):
        """Save description to database

        :param is_creation: whether an application was created via this description
        """
        ApplicationDescription.objects.create(
            application=application,
            owner=application.owner,
            **AppDescriptionSLZ(desc).data,
            # TODO: basic info
            basic_info={},
            is_creation=is_creation,
        )


def flatten_dependency_tree(dependency_tree: Dict[str, List[str]]) -> List[str]:
    """按依赖的拓扑结构将依赖关系描述树摊平成一维数组, 以保证初始化增强服务时, 不会出现引用的模块未创建对应增强服务的问题

    >>> flatten_dependency_tree({"A": ["B", "C"], "B": ["C", "D"]})
    ['C', 'D', 'B', 'A']

    >>> flatten_dependency_tree({"A": ["C", "B"], "B": ["C", "D"]})
    ['D', 'C', 'B', 'A']

    >>> flatten_dependency_tree({"A": ["B", "C"], "B": ["C", "D"], "E": []})
    ['C', 'D', 'B', 'A', 'E']

    >>> flatten_dependency_tree({"A": [], "B": ["A"], "C": ["A"]})
    ['A', 'B', 'C']
    """
    orders: List[str] = []
    for key, dependencies in dependency_tree.items():
        key_exists = key in orders
        if not key_exists:
            orders.append(key)
        i = orders.index(key)

        for dependency in dependencies:
            if dependency not in orders:
                orders.insert(i, dependency)
            elif key_exists and orders.index(dependency) > i:
                orders.pop(orders.index(dependency))
                orders.insert(i, dependency)
    return orders
