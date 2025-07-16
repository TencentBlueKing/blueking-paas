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

"""Shared service across modules"""

import logging
from typing import Dict, Iterable, List, Optional, Sequence

from django.core.exceptions import ObjectDoesNotExist

from paasng.accessories.servicehub.manager import (
    DuplicatedBindingValidator,
    EnvVariableGroup,
    SharedServiceInfo,
    get_db_properties,
    get_db_properties_by_service_type,
    mixed_service_mgr,
)
from paasng.platform.applications.models import ModuleEnvironment
from paasng.platform.modules.models import Module

from .constants import ServiceBindingType
from .exceptions import ReferencedAttachmentNotFound, SharedAttachmentAlreadyExists
from .models import SharedServiceAttachment
from .services import ServiceObj

logger = logging.getLogger(__name__)


class ServiceSharingManager:
    """Manage shared service attachments by module

    :param module: The module that shares other module's service
    """

    def __init__(self, module: Module):
        self.module = module
        self.application = module.application

    def list_shareable(self, service: ServiceObj) -> Sequence[Module]:
        """List all modules already bind with given service"""
        qs = mixed_service_mgr.get_provisioned_queryset(service, application_ids=[self.application.pk])
        return [rel.module for rel in qs if rel.module != self.module]

    def create(self, service: ServiceObj, ref_module: Module) -> SharedServiceAttachment:
        """Create a shared service relationship from given module

        :param ref_module: referenced module that holds the REAL service binding relationship.
        :raises ReferencedAttachmentNotFound: when referenced relationship not found
        :raises SharedAttachmentAlreadyExists: when shared attachment already exists
        """
        if ref_module == self.module:
            raise RuntimeError("module can not share from itself")

        DuplicatedBindingValidator(self.module, ServiceBindingType.SHARING).validate(service)

        qs = mixed_service_mgr.get_provisioned_queryset(service, application_ids=[self.application.pk])
        try:
            rel = qs.get(module=ref_module)
        except ObjectDoesNotExist:
            raise ReferencedAttachmentNotFound(f"Referenced attachment not found, module: {ref_module.name}")

        db_properties = get_db_properties(service)
        # Check duplicated creation
        if SharedServiceAttachment.objects.filter(
            module=self.module,
            service_type=db_properties.col_service_type,
            service_id=service.uuid,
        ).exists():
            raise SharedAttachmentAlreadyExists(f"already created shared attachment, ref_module: {ref_module.name}")

        return SharedServiceAttachment.objects.create(
            module=self.module,
            service_type=db_properties.col_service_type,
            service_id=service.uuid,
            ref_attachment_pk=rel.pk,
            tenant_id=self.application.tenant_id,
        )

    def list_all_shared_info(self) -> Iterable[SharedServiceInfo]:
        """List all shared service infos"""
        for obj in SharedServiceAttachment.objects.filter(module=self.module):
            referenced_info = extract_shared_info(obj)
            if not referenced_info:
                logger.error(
                    "Can not find referenced information from shared attachment: %s, data might be broken",
                    obj.pk,
                )
                continue
            yield referenced_info

    def list_shared_info(self, category: int) -> Sequence[SharedServiceInfo]:
        """List all shared service infos by service category"""
        results = []
        for referenced_info in self.list_all_shared_info():
            if referenced_info.service.category_id == category:
                results.append(referenced_info)
        return results

    def get_shared_info(self, service: ServiceObj) -> Optional[SharedServiceInfo]:
        """Get shared service info by service object

        :return: None if no shared info can be found
        """
        try:
            obj = SharedServiceAttachment.objects.get(module=self.module, service_id=service.uuid)
        except ObjectDoesNotExist:
            return None
        return extract_shared_info(obj)

    def destroy(self, service: ServiceObj):
        """Destroy a shared relationship"""
        SharedServiceAttachment.objects.filter(module=self.module, service_id=service.uuid).delete()

    def get_env_variables(self, env: ModuleEnvironment, filter_enabled: bool = False) -> Dict[str, str]:
        """Get all env variables shared from other modules

        :param env: ModuleEnvironment object, must belongs to self.module
        :param filter_enabled: Whether to filter enabled service instances
        :return: A dict of environment variables.
        """
        ret = {}
        for g in self.get_env_variable_groups(env, filter_enabled):
            ret.update(g.data)
        return ret

    def get_env_variable_groups(self, env: ModuleEnvironment, filter_enabled: bool = False) -> List[EnvVariableGroup]:
        """Get all env variable groups shared from other modules.

        :param env: ModuleEnvironment object, must belongs to self.module
        :param filter_enabled: Whether to filter enabled service instances
        :return: A list of EnvVariableGroup objects.
        """
        if env.module != self.module:
            raise RuntimeError("Invalid env object, must belongs to self.module")

        results = []
        for referenced_info in self.list_all_shared_info():
            ref_env = referenced_info.ref_module.get_envs(env.environment)
            groups = mixed_service_mgr.get_env_var_groups(ref_env.engine_app, referenced_info.service, filter_enabled)
            results.extend(groups)
        return results


def extract_shared_info(attachment: SharedServiceAttachment) -> Optional[SharedServiceInfo]:
    """Extract shared service information by attachment object

    :param attachment: SharedServiceAttachment object
    :return: None if the referenced object was not found
    """
    db_props = get_db_properties_by_service_type(attachment.service_type)
    try:
        referenced_rel = db_props.model_module_rel.objects.get(pk=attachment.ref_attachment_pk)
    except ObjectDoesNotExist:
        return None

    return SharedServiceInfo(
        service=mixed_service_mgr.get(referenced_rel.service_id),
        module=attachment.module,
        ref_module=referenced_rel.module,
    )


class SharingReferencesManager:
    """Manage sharing references"""

    def __init__(self, module: Module):
        self.module = module
        self.application = module.application

    def list_related_modules(self, service: ServiceObj) -> Sequence[Module]:
        """Find all modules which are sharing self.module's service"""
        shared_attachments = SharedServiceAttachment.objects.list_by_ref_module(service, self.module)
        return [obj.module for obj in shared_attachments]

    def clear_related(self, service: ServiceObj):
        """Clear all sharing relationships"""
        shared_attachments = SharedServiceAttachment.objects.list_by_ref_module(service, self.module)
        for attachment in shared_attachments:
            attachment.delete()
