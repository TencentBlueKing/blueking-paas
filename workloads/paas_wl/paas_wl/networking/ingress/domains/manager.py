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
"""Manage application's custom domains"""
import logging
from typing import Dict, Optional, Protocol, Type

from django.db import IntegrityError, transaction
from rest_framework.exceptions import ValidationError
from rest_framework.serializers import Serializer

from paas_wl.cnative.specs.resource import deploy_networking
from paas_wl.networking.ingress.config import get_custom_domain_config
from paas_wl.networking.ingress.domains.exceptions import ReplaceAppDomainFailed
from paas_wl.networking.ingress.domains.independent import (
    DomainResourceDeleteService,
    ReplaceAppDomainService,
    get_service_name,
)
from paas_wl.networking.ingress.exceptions import ValidCertNotFound
from paas_wl.networking.ingress.managers import CustomDomainIngressMgr
from paas_wl.networking.ingress.models import Domain
from paas_wl.platform.applications.models import WlApp
from paas_wl.utils.error_codes import error_codes
from paas_wl.workloads.processes.controllers import module_env_is_running
from paasng.platform.applications.constants import ApplicationType
from paasng.platform.applications.models import Application, ModuleEnvironment
from paasng.publish.market.models import MarketConfig
from paasng.publish.market.utils import MarketAvailableAddressHelper

logger = logging.getLogger(__name__)


class CustomDomainManager(Protocol):
    """Manage custom domains for different kinds of applications"""

    def create(self, *, env: ModuleEnvironment, host: str, path_prefix: str, https_enabled: bool) -> Domain:
        """Create a custom domain"""
        ...

    def update(self, instance: Domain, *, host: str, path_prefix: str, https_enabled: bool) -> Domain:
        """Update a custom domain"""
        ...

    def delete(self, instance: Domain) -> None:
        """Delete a custom domain"""
        ...


class DftCustomDomainManager:
    """This manager was designed to be directly used by views

    :param application: The application to be managed
    """

    def __init__(self, application: Application):
        self.application = application

    @transaction.atomic
    def create(self, *, env: ModuleEnvironment, host: str, path_prefix: str, https_enabled: bool) -> Domain:
        """Create a custom domain

        :param env: The environment to which the domain binds
        :param host: Hostname of domain
        :param path_prefix: The path prefix of domain
        :param https_enabled: whether HTTPS is enabled
        :raise ValidationError: when input is not valid, such as host is duplicated
        """
        if not module_env_is_running(env):
            raise ValidationError('未部署的环境无法添加独立域名，请先部署对应环境')

        wl_app = WlApp.objects.get_by_env(env)
        service_name = get_service_name(wl_app)
        try:
            domain, _ = Domain.objects.update_or_create(
                name=host,
                path_prefix=path_prefix,
                module_id=env.module_id,
                environment_id=env.id,
                defaults={"https_enabled": https_enabled},
            )
            CustomDomainIngressMgr(domain).sync(default_service_name=service_name)
        except ValidCertNotFound:
            raise error_codes.CREATE_CUSTOM_DOMAIN_FAILED.f("找不到有效的 TLS 证书")
        except IntegrityError:
            raise error_codes.CREATE_CUSTOM_DOMAIN_FAILED.f(f"域名 {host} 已被占用")
        except Exception:
            logger.exception("create custom domain failed")
            raise error_codes.CREATE_CUSTOM_DOMAIN_FAILED.f("未知错误")
        return domain

    @transaction.atomic
    def update(self, instance: Domain, *, host: str, path_prefix: str, https_enabled: bool) -> Domain:
        """Update a custom domain object"""
        if check_domain_used_by_market(self.application, instance.name):
            raise error_codes.UPDATE_CUSTOM_DOMAIN_FAILED.f('该域名已被绑定为主访问入口, 请解绑后再进行更新操作')

        env = ModuleEnvironment.objects.get(pk=instance.environment_id)
        try:
            svc = ReplaceAppDomainService(env, instance.name, instance.path_prefix)
            svc.replace_with(host, path_prefix, https_enabled)
        except ReplaceAppDomainFailed as e:
            raise error_codes.UPDATE_CUSTOM_DOMAIN_FAILED.f(str(e))
        return instance

    @transaction.atomic
    def delete(self, instance: Domain) -> None:
        """Delete a custom domain"""
        if check_domain_used_by_market(self.application, instance.name):
            raise error_codes.DELETE_CUSTOM_DOMAIN_FAILED.f('该域名已被绑定为主访问入口, 请解绑后再进行删除操作')

        env = ModuleEnvironment.objects.get(pk=instance.environment_id)
        ret = DomainResourceDeleteService(env).do(host=instance.name, path_prefix=instance.path_prefix)
        if not ret:
            raise error_codes.DELETE_CUSTOM_DOMAIN_FAILED.f("无法删除集群中域名访问记录")


def validate_domain_payload(
    data: Dict,
    application: Application,
    serializer_cls: Type[Serializer],
    instance: Optional[Domain] = None,
):
    """Validate a domain data, which was read form user input

    :param application: The application which domain belongs to
    :param instance: Optional Domain object, must provide when perform updating
    :param serializer_slz: Optional serializer type, if not given, use DomainSLZ
    """
    serializer = serializer_cls(
        data=data,
        instance=instance,
        context={
            'valid_domain_suffixes': get_custom_domain_config(application.region).valid_domain_suffixes,
        },
    )
    serializer.is_valid(raise_exception=True)
    return serializer.validated_data


def check_domain_used_by_market(application: Application, hostname: str) -> bool:
    """Check if a domain was used as application's market entrance

    :param hostname: A domain name without scheme
    :return: Whether hostname was set as entrance
    """
    market_config, _ = MarketConfig.objects.get_or_create_by_app(application)
    entrance = MarketAvailableAddressHelper(market_config).access_entrance
    if not entrance:
        return False
    return entrance.hostname == hostname


# cloud-native related managers starts


class CNativeCustomDomainManager:
    """Manage custom domains for cloud native applications

    * This manager was designed to be directly used by views

    :param application: The application to be managed
    """

    def __init__(self, application: Application):
        self.application = application

    @transaction.atomic
    def create(self, *, env: ModuleEnvironment, host: str, path_prefix: str, https_enabled: bool) -> Domain:
        """Create a custom domain

        :param env: The environment to which the domain binds
        :param host: Hostname of domain
        :param path_prefix: The path prefix of domain
        :param https_enabled: whether HTTPS is enabled
        :raise ValidationError: when input is not valid, such as host is duplicated
        """
        if not module_env_is_running(env):
            raise ValidationError('未部署的环境无法添加独立域名，请先部署对应环境')

        # Create the domain object first, so the later deploy process can read it
        domain = Domain.objects.create(
            module_id=env.module.id,
            environment_id=env.id,
            name=host,
            path_prefix=path_prefix,
            https_enabled=https_enabled,
        )

        try:
            deploy_networking(env)
        except Exception:
            logger.exception("Create custom domain for c-native app failed")
            raise error_codes.CREATE_CUSTOM_DOMAIN_FAILED.f("未知错误")
        return domain

    @transaction.atomic
    def update(self, instance: Domain, *, host: str, path_prefix: str, https_enabled: bool) -> Domain:
        """Update a custom domain"""
        if check_domain_used_by_market(self.application, instance.name):
            raise error_codes.UPDATE_CUSTOM_DOMAIN_FAILED.f('该域名已被绑定为主访问入口, 请解绑后再进行更新操作')

        # Update Domain instance
        instance.name = host
        instance.path_prefix = path_prefix
        instance.https_enabled = https_enabled
        instance.save()

        environment = self.application.get_module(instance.module.name).get_envs(instance.environment.environment)
        try:
            deploy_networking(environment)
        except Exception as e:
            logger.exception("Update custom domain for c-native app failed")
            raise error_codes.UPDATE_CUSTOM_DOMAIN_FAILED.f(str(e))
        return instance

    @transaction.atomic
    def delete(self, instance: Domain) -> None:
        """Delete a custom domain"""
        if check_domain_used_by_market(self.application, instance.name):
            raise error_codes.DELETE_CUSTOM_DOMAIN_FAILED.f('该域名已被绑定为主访问入口, 请解绑后再进行删除操作')

        # Delete the instance first so `deploy_networking` won't include it.
        instance.delete()
        environment = self.application.get_module(instance.module.name).get_envs(instance.environment.environment)
        try:
            deploy_networking(environment)
        except Exception:
            logger.exception("Delete custom domain for c-native app failed")
            raise error_codes.DELETE_CUSTOM_DOMAIN_FAILED.f("无法删除集群中域名访问记录")


def get_custom_domain_mgr(application: Application) -> CustomDomainManager:
    """Get a manager for managing custom domain"""
    if application.type == ApplicationType.CLOUD_NATIVE:
        return CNativeCustomDomainManager(application)
    return DftCustomDomainManager(application)
