# -*- coding: utf-8 -*-
"""Utilities for managing independent domains"""
import contextlib
import copy
import logging

from django.db import IntegrityError, transaction

from paas_wl.networking.ingress.constants import AppDomainSource
from paas_wl.networking.ingress.exceptions import PersistentAppDomainRequired, ValidCertNotFound
from paas_wl.networking.ingress.managers import CustomDomainIngressMgr
from paas_wl.networking.ingress.models import AppDomain
from paas_wl.networking.ingress.utils import get_main_process_service_name, guess_default_service_name
from paas_wl.platform.applications.models import EngineApp
from paas_wl.resources.kube_res.exceptions import AppEntityNotFound

from .exceptions import ReplaceAppDomainFailed

logger = logging.getLogger(__name__)


@contextlib.contextmanager
def restore_ingress_on_error(app_domain: AppDomain, service_name: str):
    """A context manager which syncs a domain's ingress resource when exception happenes"""
    try:
        yield
    except Exception:
        logger.warning('Exception happened in `restore_ingress_on_error` block, will sync ingress resource.')
        CustomDomainIngressMgr(app_domain).sync(default_service_name=service_name)
        raise


class ReplaceAppDomainService:
    """Service to perform AppDomain replacement

    :param host: used for locating original domain object
    :param path_prefix: used for locating original domain object
    """

    def __init__(self, app: EngineApp, host: str, path_prefix: str):
        self.app = app
        self.host = host
        self.path_prefix = path_prefix
        self.domain_obj = self._get_obj()

    def _get_obj(self) -> AppDomain:
        try:
            return AppDomain.objects.get(
                region=self.app.region,
                app=self.app,
                source=AppDomainSource.INDEPENDENT,
                host=self.host,
                path_prefix=self.path_prefix,
            )
        except AppDomain.DoesNotExist:
            raise ReplaceAppDomainFailed("无法找到旧域名记录，请稍后重试")

    @transaction.atomic
    def replace_with(self, host: str, path_prefix, https_enabled: bool):
        """Replace current AppDomain object"""
        # Save a copy of old data to perfor deletion later
        old_copy_obj = copy.deepcopy(self.domain_obj)
        # Try modify the database object first

        self.domain_obj.host = host
        self.domain_obj.path_prefix = path_prefix
        self.domain_obj.https_enabled = https_enabled
        try:
            self.domain_obj.save()
        except IntegrityError:
            raise ReplaceAppDomainFailed(f"域名记录 {host}{path_prefix} 已被占用")

        service_name = get_service_name(self.app)
        try:
            with restore_ingress_on_error(old_copy_obj, service_name):
                # Delete the old ingress resource first, then create a new one.
                #
                # WARNING: although `restore_ingress_on_error` will try restore the old ingress resource
                # when exception was raised, but this is not really "transactional". If there is something
                # wrong with the "restoring" procedure, we will be left at a dangerous situation where
                # the ingress was absent--deletion finished, creation and restoring failed.
                CustomDomainIngressMgr(old_copy_obj).delete()
                CustomDomainIngressMgr(self.domain_obj).sync(default_service_name=service_name)
        except ValidCertNotFound:
            raise ReplaceAppDomainFailed("找不到有效的 TLS 证书")
        except Exception:
            logger.exception("replace ingress failed")
            raise ReplaceAppDomainFailed("未知错误，请稍后重试")


class DomainResourceCreateService:
    """Create custom domain related resources, such as Kubernetes Ingress resource and AppDomain
    records(the data which prevent duplicated domains in one cluster)
    """

    def __init__(self, engine_app: EngineApp):
        self.engine_app = engine_app

    def do(self, *, host: str, path_prefix: str, https_enabled: bool):
        """Create a custom domain"""
        service_name = get_service_name(self.engine_app)
        domain_ins, _ = AppDomain.objects.update_or_create(
            region=self.engine_app.region,
            app=self.engine_app,
            source=AppDomainSource.INDEPENDENT,
            host=host,
            path_prefix=path_prefix,
            defaults={'https_enabled': https_enabled},
        )
        CustomDomainIngressMgr(domain_ins).sync(default_service_name=service_name)


class DomainResourceDeleteService:
    """Delete custom domain related resources"""

    def __init__(self, engine_app: EngineApp):
        self.engine_app = engine_app

    def do(self, *, host: str, path_prefix: str) -> bool:
        """Delete a domain by given condition

        :return: bool value, whether deletion successfully finished
        """
        db_or_mem_domain = self._get_app_domain_for_deletion(host, path_prefix)
        try:
            CustomDomainIngressMgr(db_or_mem_domain).delete()
        except PersistentAppDomainRequired:
            # When deleting a domain with customized path prefix, a persistent object is alway required
            # because it's "id" used in ingress resource name, consider as a success when it happens.
            logger.warning("Persistent object was required for deleting ingress, obj=%s", db_or_mem_domain)
            return True
        except Exception:
            logger.exception("delete ingress failed")
            return False

        if db_or_mem_domain.id:
            db_or_mem_domain.delete()
        return True

    def _get_app_domain_for_deletion(self, host: str, path_prefix: str) -> AppDomain:
        """Get a AppDomain object for deletion, when not entry can be found via given kwargs, will
        make an in-memory object instead, which is still useful for deleting Ingress resource
        """
        fields = dict(
            region=self.engine_app.region,
            app=self.engine_app,
            source=AppDomainSource.INDEPENDENT,
            host=host,
            path_prefix=path_prefix,
        )
        try:
            return AppDomain.objects.get(**fields)
        except AppDomain.DoesNotExist:
            logger.warning(
                'AppDomain record: %s-%s no longer exists in database, skip deletion',
                fields['host'],
                fields['path_prefix'],
            )
            return AppDomain(**fields)


def get_service_name(app) -> str:
    """Get service name for creating new ingress resources. By default, app's all Ingresses
    should point to the same Service."""
    try:
        return get_main_process_service_name(app)
    except AppEntityNotFound:
        return guess_default_service_name(app)
