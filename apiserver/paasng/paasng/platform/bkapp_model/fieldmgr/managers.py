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
    """This class helps manage the management status of an module's bkapp model field.
    If the field is unmanaged and the default manager was given, it can be managed by the default manager.

    :param module: The module object.
    :param field: The field to be managed.
    :param default_manager: The default manager. The field can be managed by the default manager if it is unmanaged.
    """

    def __init__(self, module: Module, field: Field, default_manager: Optional[FieldMgrName] = None):
        self.module = module
        self.field = field
        self.store = RowGroupStore(module)
        self.row_group = self.store.get()

        self._default_manager = default_manager

    def can_be_managed_by(self, manager: FieldMgrName) -> bool:
        """Check if current field can be managed by the given manager."""
        return manager == (self.get() or self._default_manager)

    def get(self) -> Optional[FieldMgrName]:
        """Get the manager for the field from row group store.

        :return: The manager for the field, or None if the field is not managed.
        """
        return self.row_group.get_manager(self.field)

    def set(self, manager: FieldMgrName):
        """Set the manager for the field.

        :param manager: The manager to be set.
        """
        self.row_group.set_manager(self.field, manager)
        self.store.save(self.row_group)

    def reset(self):
        """Reset the manager to empty for the field."""
        self.row_group.reset_manager(self.field)
        self.store.save(self.row_group)


class MultiFieldsManager:
    """This class helps manage the management status of an module's bkapp model field,
    It's able to manage multiple fields at the same time.

    :param module: The module object.
    """

    def __init__(self, module: Module):
        self.module = module
        self.store = RowGroupStore(module)
        self.row_group = self.store.get()

    def set_many(self, fields: list[Field], manager: FieldMgrName):
        """Set the manager for many fields.

        :param fields: The fields to be managed.
        :param manager: The manager to be set.
        """
        for f in fields:
            self.row_group.set_manager(f, manager)
        self.store.save(self.row_group)

    def reset_many(self, fields: list[Field]):
        """Reset the manager for many fields.

        :param fields: The fields to be managed.
        """
        for f in fields:
            self.row_group.reset_manager(f)
        self.store.save(self.row_group)

    def get(self, fields: list[Field]) -> dict[Field, Optional[FieldMgrName]]:
        """Get manager for each field in fields."""
        return {f: self.row_group.get_manager(f) for f in fields}


class RowGroupStore:
    """The managed fields row group store.

    :param module: The module object.
    """

    def __init__(self, module: Module):
        self.module = module

    def get(self) -> ManagerFieldsRowGroup:
        """Get the managed fields instance of the module."""
        db_rows = self.module.managed_fields.all()
        rows = [ManagerFieldsRow(FieldMgrName(record.manager), record.fields) for record in db_rows]
        return ManagerFieldsRowGroup(rows)

    def save(self, row_group: ManagerFieldsRowGroup):
        """Save a row_group to make the data persistent."""
        for record in row_group.get_updated_rows():
            BkAppManagedFields.objects.update_or_create(
                module=self.module,
                manager=record.manager,
                defaults={"fields": record.fields, "tenant_id": self.module.tenant_id},
            )
        row_group.clean_updated()
