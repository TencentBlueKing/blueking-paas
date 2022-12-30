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
"""Utilities for managing independent domains"""
import contextlib
import copy
import logging

from django.db import IntegrityError, transaction

from paas_wl.networking.ingress.exceptions import PersistentAppDomainRequired, ValidCertNotFound
from paas_wl.networking.ingress.managers import CustomDomainIngressMgr
from paas_wl.networking.ingress.models import Domain
from paas_wl.networking.ingress.utils import get_main_process_service_name, guess_default_service_name
from paas_wl.platform.applications.models import EngineApp
from paas_wl.platform.applications.struct_models import ModuleEnv
from paas_wl.resources.kube_res.exceptions import AppEntityNotFound

from .exceptions import ReplaceAppDomainFailed

logger = logging.getLogger(__name__)


@contextlib.contextmanager
def restore_ingress_on_error(domain: Domain, service_name: str):
    """A context manager which syncs a domain's ingress resource when exception happenes"""
    try:
        yield
    except Exception:
        logger.warning('Exception happened in `restore_ingress_on_error` block, will sync ingress resource.')
        CustomDomainIngressMgr(domain).sync(default_service_name=service_name)
        raise


class ReplaceAppDomainService:
    """Service to perform AppDomain replacement

    :param host: used for locating original domain object
    :param path_prefix: used for locating original domain object
    """

    def __init__(self, env: ModuleEnv, host: str, path_prefix: str):
        self.engine_app = EngineApp.objects.get_by_env(env)
        self.env = env
        self.host = host
        self.path_prefix = path_prefix
        self.domain_obj = self._get_obj()

    def _get_obj(self) -> Domain:
        try:
            return Domain.objects.get(
                name=self.host,
                path_prefix=self.path_prefix,
                module_id=self.env.module_id,
                environment_id=self.env.id,
            )
        except Domain.DoesNotExist:
            raise ReplaceAppDomainFailed("无法找到旧域名记录，请稍后重试")

    @transaction.atomic
    def replace_with(self, host: str, path_prefix, https_enabled: bool):
        """Replace current AppDomain object"""
        # Save a copy of old data to perform deletion later
        old_copy_obj = copy.deepcopy(self.domain_obj)
        # Try modify the database object first

        self.domain_obj.name = host
        self.domain_obj.path_prefix = path_prefix
        self.domain_obj.https_enabled = https_enabled
        try:
            self.domain_obj.save()
        except IntegrityError:
            raise ReplaceAppDomainFailed(f"域名记录 {host}{path_prefix} 已被占用")

        service_name = get_service_name(self.engine_app)
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


class DomainResourceDeleteService:
    """Delete custom domain related resources"""

    def __init__(self, env: ModuleEnv):
        self.engine_app = EngineApp.objects.get_by_env(env)
        self.env = env

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

    def _get_app_domain_for_deletion(self, host: str, path_prefix: str) -> Domain:
        """Get a AppDomain object for deletion, when not entry can be found via given kwargs, will
        make an in-memory object instead, which is still useful for deleting Ingress resource
        """
        fields = dict(
            name=host,
            path_prefix=path_prefix,
            module_id=self.env.module_id,
            environment_id=self.env.id,
        )
        try:
            return Domain.objects.get(**fields)
        except Domain.DoesNotExist:
            logger.warning('AppDomain record: %s-%s no longer exists in database, skip deletion', host, path_prefix)
            return Domain(**fields)


def get_service_name(app) -> str:
    """Get service name for creating new ingress resources. By default, app's all Ingresses
    should point to the same Service."""
    try:
        return get_main_process_service_name(app)
    except AppEntityNotFound:
        return guess_default_service_name(app)
