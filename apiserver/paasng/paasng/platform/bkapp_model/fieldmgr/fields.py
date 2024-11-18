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

from .constants import FieldMgrName

Field: TypeAlias = str


# Some predefined fields and factories
F_SVC_DISCOVERY: Field = "spec.svcDiscovery"
F_DOMAIN_RESOLUTION: Field = "spec.domainResolution"
F_HOOKS: Field = "spec.hooks"


def f_overlay_replicas(process: str, env_name: str) -> Field:
    return f"spec.envOverlay.replicas[{process}:{env_name}]"


def f_overlay_autoscaling(process: str, env_name: str) -> Field:
    return f"spec.envOverlay.autoscaling[{process}:{env_name}]"


def f_overlay_res_quotas(process: str, env_name: str) -> Field:
    return f"spec.envOverlay.resQuotas[{process}:{env_name}]"


def f_overlay_mounts(process: str, env_name: str) -> Field:
    return f"spec.envOverlay.mounts[{process}:{env_name}]"


@define
class ManagerFieldsRow:
    """A simple row data structure that contains a manager and the fields it manages.
    Used with `ManagerFieldsRowGroup`.
    """

    manager: FieldMgrName
    fields: List[Field] = field(factory=list)

    def contains(self, field: Field) -> bool:
        """Check if current row contains the field"""
        return field in self.fields

    def add(self, field: Field) -> bool:
        """Add a field to the current row.

        :return: Whether the current row has been modified.
        """
        if self.contains(field):
            return False
        self.fields.append(field)
        return True

    def remove(self, field: Field) -> bool:
        """Remove a field from the current row.

        :return: Whether the current row has been modified.
        """
        try:
            self.fields.remove(field)
        except ValueError:
            return False
        else:
            return True


class ManagerFieldsRowGroup:
    """A group of `ManagerFieldsRow` containing data from multiple managers, this
    class manages many rows at once.

    The main advantage of using this class is that it does the field manager management
    in memory, so the client can perform multiple operations before saving, such as
    setting the manager for many fields. for data-persistency see `get_updated_rows()`.

    An example rows:

    - (WEB_FORM, ['filed1'])
    - (APP_DESC, ['filed2', 'field3'])

    :param rows: A list of (manager, fields) row.
    :raise ValueError: When the given rows are invalid.
    """

    def __init__(self, rows: List[ManagerFieldsRow]):
        self.rows = rows
        self._validate_rows()

        # When the row has been modified, it's manager will be added to the "updated"
        # set so that the client can be notified for saving the changes.
        self._updated_managers: set[FieldMgrName] = set()

    def _validate_rows(self):
        """Validate the current rows to make sure the data is correct."""
        managers = [r.manager for r in self.rows]
        if len(managers) != len(set(managers)):
            raise ValueError("Duplicated managers are not allowed.")

    def get_manager(self, field: Field) -> Optional[FieldMgrName]:
        """Get the current manager by field.

        :param field: The field to check.
        :return: The manager, or None if not found.
        """
        for row in self.rows:
            if row.contains(field):
                return row.manager
        return None

    def set_manager(self, field: Field, manager: FieldMgrName):
        """Set the field to be managed by the given manager."""
        found_in_rows = False
        for row in self.rows:
            if row.manager == manager:
                found_in_rows = True
                if row.add(field):
                    self._updated_managers.add(row.manager)
            # Remove the field from other managers
            elif row.remove(field):
                self._updated_managers.add(row.manager)

        # Add a new rows when the manager is not found
        if not found_in_rows:
            self.rows.append(ManagerFieldsRow(manager=manager, fields=[field]))
            self._updated_managers.add(manager)

    def reset_manager(self, field: Field):
        """Reset the field to be not managed by any managers."""
        for row in self.rows:
            if row.remove(field):
                self._updated_managers.add(row.manager)

    def get_updated_rows(self) -> list[ManagerFieldsRow]:
        """Get the rows that have been modified."""
        results = []
        for r in self.rows:
            if r.manager in self._updated_managers:
                results.append(r)
        return results
