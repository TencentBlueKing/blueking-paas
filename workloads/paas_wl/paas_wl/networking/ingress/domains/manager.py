"""Manage application's custom domains"""
import logging
from typing import Dict, Optional, Protocol, Type
from urllib.parse import urlparse

from django.db import IntegrityError, transaction
from rest_framework.exceptions import ValidationError
from rest_framework.serializers import Serializer

from paas_wl.cnative.specs.resource import deploy_networking
from paas_wl.networking.ingress.config import get_custom_domain_config
from paas_wl.networking.ingress.exceptions import ValidCertNotFound
from paas_wl.networking.ingress.models import Domain
from paas_wl.networking.ingress.serializers import DomainSLZ
from paas_wl.platform.applications.constants import ApplicationType
from paas_wl.platform.applications.models import EngineApp
from paas_wl.platform.applications.struct_models import Application, ModuleEnv, to_structured
from paas_wl.platform.external.client import get_plat_client
from paas_wl.utils.error_codes import error_codes
from paas_wl.workloads.processes.controllers import env_is_running

from .exceptions import ReplaceAppDomainFailed
from .independent import DomainResourceCreateService, DomainResourceDeleteService, ReplaceAppDomainService

logger = logging.getLogger(__name__)


class CustomDomainManager(Protocol):
    """Manage custom domains for different kinds of applications"""

    def create(self, *, env: ModuleEnv, host: str, path_prefix: str, https_enabled: bool) -> Domain:
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
    def create(self, *, env: ModuleEnv, host: str, path_prefix: str, https_enabled: bool) -> Domain:
        """Create a custom domain

        :param env: The environment to which the domain binds
        :param host: Hostname of domain
        :param path_prefix: The path prefix of domain
        :param https_enabled: whether HTTPS is enabled
        :raise ValidationError: when input is not valid, such as host is duplicated
        """
        if not env_is_running(env):
            raise ValidationError('未部署的环境无法添加独立域名，请先部署对应环境')

        engine_app = EngineApp.objects.get(pk=env.engine_app_id)
        try:
            DomainResourceCreateService(engine_app).do(host=host, path_prefix=path_prefix, https_enabled=https_enabled)
        except ValidCertNotFound:
            raise error_codes.CREATE_CUSTOM_DOMAIN_FAILED.f("找不到有效的 TLS 证书")
        except IntegrityError:
            raise error_codes.CREATE_CUSTOM_DOMAIN_FAILED.f(f"域名 {host} 已被占用")
        except Exception:
            logger.exception("create custom domain failed")
            raise error_codes.CREATE_CUSTOM_DOMAIN_FAILED.f("未知错误")

        return Domain.objects.create(
            module_id=env.module.id,
            environment_id=env.id,
            name=host,
            path_prefix=path_prefix,
            https_enabled=https_enabled,
        )

    @transaction.atomic
    def update(self, instance: Domain, *, host: str, path_prefix: str, https_enabled: bool) -> Domain:
        """Update a custom domain object"""
        if check_domain_used_by_market(self.application, instance.name):
            raise error_codes.UPDATE_CUSTOM_DOMAIN_FAILED.f('该域名已被绑定为主访问入口, 请解绑后再进行更新操作')

        engine_app = EngineApp.objects.get(pk=instance.environment.engine_app_id)
        try:
            svc = ReplaceAppDomainService(engine_app, instance.name, instance.path_prefix)
            svc.replace_with(host, path_prefix, https_enabled)
        except ReplaceAppDomainFailed as e:
            raise error_codes.UPDATE_CUSTOM_DOMAIN_FAILED.f(str(e))

        # Update Domain instance
        instance.name = host
        instance.path_prefix = path_prefix
        instance.https_enabled = https_enabled
        instance.save()
        return instance

    @transaction.atomic
    def delete(self, instance: Domain) -> None:
        """Delete a custom domain"""
        if check_domain_used_by_market(self.application, instance.name):
            raise error_codes.DELETE_CUSTOM_DOMAIN_FAILED.f('该域名已被绑定为主访问入口, 请解绑后再进行删除操作')

        engine_app = EngineApp.objects.get(pk=instance.environment.engine_app_id)
        ret = DomainResourceDeleteService(engine_app).do(host=instance.name, path_prefix=instance.path_prefix)
        if not ret:
            raise error_codes.DELETE_CUSTOM_DOMAIN_FAILED.f("无法删除集群中域名访问记录")
        instance.delete()


def validate_domain_payload(
    data: Dict,
    application: Application,
    instance: Optional[Domain] = None,
    serializer_cls: Type[Serializer] = DomainSLZ,
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
            'application': application,
            'struct_app': to_structured(application),
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
    ret = get_plat_client().get_market_entrance(application.code)
    entrance = ret['entrance']
    if not (entrance and entrance.get('address')):
        return False
    return urlparse(entrance['address']).hostname == hostname


# cloud-native related managers starts


class CNativeCustomDomainManager:
    """Manage custom domains for cloud native applications

    * This manager was designed to be directly used by views

    :param application: The application to be managed
    """

    def __init__(self, application: Application):
        self.application = application

    @transaction.atomic
    def create(self, *, env: ModuleEnv, host: str, path_prefix: str, https_enabled: bool) -> Domain:
        """Create a custom domain

        :param env: The environment to which the domain binds
        :param host: Hostname of domain
        :param path_prefix: The path prefix of domain
        :param https_enabled: whether HTTPS is enabled
        :raise ValidationError: when input is not valid, such as host is duplicated
        """
        if not env_is_running(env):
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

        try:
            deploy_networking(instance.environment)
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

        try:
            deploy_networking(instance.environment)
        except Exception:
            logger.exception("Delete custom domain for c-native app failed")
            raise error_codes.DELETE_CUSTOM_DOMAIN_FAILED.f("无法删除集群中域名访问记录")


def get_custom_domain_mgr(application: Application) -> CustomDomainManager:
    """Get a manager for managing custom domain"""
    if application.type == ApplicationType.CLOUD_NATIVE:
        return CNativeCustomDomainManager(application)
    return DftCustomDomainManager(application)
