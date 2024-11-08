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

from typing import List, Optional, TypeAlias

from attrs import define, field

from paasng.platform.modules.models import Module

from .constants import ManagerType

Field: TypeAlias = str


# Some predefined fields and factories
F_SVC_DISCOVERY: Field = "spec.svcDiscovery"
F_DOMAIN_RESOLUTION: Field = "spec.domainResolution"


def f_overlay_replicas(process: str, env_name: str) -> Field:
    return "spec.envOverlay.replicas[{process}:{env_name}]"


def f_overlay_autoscaling(process: str, env_name: str) -> Field:
    return "spec.envOverlay.autoscaling[{process}:{env_name}]"


def f_overlay_res_quotas(process: str, env_name: str) -> Field:
    return "spec.envOverlay.resQuotas[{process}:{env_name}]"


def f_overlay_mounts(process: str, env_name: str) -> Field:
    return "spec.envOverlay.mounts[{process}:{env_name}]"


@define
class ManagedFieldsRecord:
    """A record of a manager's managed fields."""

    manager: ManagerType
    fields: List[Field] = field(factory=list)

    def contains(self, field: Field) -> bool:
        """Check if the field are managed"""
        return field in self.fields

    def add(self, field: Field) -> bool:
        """Add a field to be managed.

        :return: Whether the add action is performed, return False if the field is
            already managed.
        """
        if self.contains(field):
            return False
        self.fields.append(field)
        return True

    def remove(self, field: Field) -> bool:
        """Remove a field from managed.

        :return: Whether the field is removed, return False if the field is not managed.
        """
        try:
            self.fields.remove(field)
        except ValueError:
            return False
        else:
            return True


class ManagedFields:
    """A module's managed fields.

    :param module: The module object.
    :param records: A list of managed fields records.
    """

    def __init__(self, module: Module, records: List[ManagedFieldsRecord]):
        self.module = module
        self.records = records

        # When the record has been modified, it's manager will be added to the dirty
        # set so that the client can be notified for saving the changes.
        self._dirty_managers: set[ManagerType] = set()

    def get_manager(self, field: Field) -> Optional[ManagerType]:
        """Get the current manager by given field.

        :param field: The field to check.
        :return: The manager, or None if not found.
        """
        for record in self.records:
            if record.contains(field):
                return record.manager
        return None

    def set_manager(self, field: Field, manager: ManagerType):
        """Set the field to be managed by the given manager."""
        for record in self.records:
            if record.manager == manager:
                if record.add(field):
                    self._dirty_managers.add(record.manager)
                return

            # Remove the field from other managers
            if record.remove(field):
                self._dirty_managers.add(record.manager)

        # Add a new record when the manager is not found in the records
        self.records.append(ManagedFieldsRecord(manager=manager, fields=[field]))
        self._dirty_managers.add(manager)

    def get_dirty_records(self) -> list[ManagedFieldsRecord]:
        """Get the dirty records that have been modified."""
        results = []
        for r in self.records:
            if r.manager in self._dirty_managers:
                results.append(r)
        return results
