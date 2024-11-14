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


from typing import Optional

from paasng.platform.bkapp_model.models import BkAppManagedFields
from paasng.platform.modules.models import Module

from .constants import FieldMgrName
from .fields import Field, ManagerFieldsRow, ManagerFieldsRowGroup


class FieldManager:
    """This class help manage the management status of an module's bkapp model field.

    :param module: The module object.
    :param field: The field to be managed.
    """

    def __init__(self, module: Module, field: Field):
        self.module = module
        self.field = field
        self.row_group = self._get_row_group(module)

    def is_managed_by(self, manager: FieldMgrName) -> bool:
        """Check if current field is managed by the given manager."""
        return self.get() == manager

    def get(self) -> Optional[FieldMgrName]:
        """Get the manager for the field.

        :return: The manager for the field, or None if the field is not managed.
        """
        return self.row_group.get_manager(self.field)

    def set(self, manager: FieldMgrName):
        """Set the manager for the field.

        :param manager: The manager to be set.
        """
        self.row_group.set_manager(self.field, manager)
        self._save()

    def reset(self):
        """Reset the manager to empty for the field."""
        self.row_group.reset_manager(self.field)
        self._save()

    def _save(self):
        """Save the changes to the database to make the data persistent."""
        for record in self.row_group.get_updated_rows():
            BkAppManagedFields.objects.update_or_create(
                module=self.module, manager=record.manager, defaults={"fields": record.fields}
            )
        # Refresh the rows group instance in memory
        self.row_group = self._get_row_group(self.module)

    @staticmethod
    def _get_row_group(module: Module) -> ManagerFieldsRowGroup:
        """Get the managed fields instance of the module."""
        db_rows = module.managed_fields.all()
        rows = [ManagerFieldsRow(FieldMgrName(record.manager), record.fields) for record in db_rows]
        return ManagerFieldsRowGroup(rows)
