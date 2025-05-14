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
"""The different roles of the system API client."""

from typing import Dict, Type

from rest_framework.permissions import BasePermission

from paasng.utils.error_codes import error_codes

from .constants import ClientAction, ClientRole


class ClientPermChecker:
    """This type helps to check if a role has a permission."""

    def __init__(self):
        self.roles: dict[ClientRole, dict] = {}
        role_perms = self._build_role_perms()
        for role in ClientRole:
            try:
                self._add_role(role, role_perms[role])
            except KeyError:
                raise ValueError(f"Role {role} is not defined in the permission map")

    def role_can_do(self, role: ClientRole, action: ClientAction) -> bool:
        """Check if a role can do an action.

        :param role: The role to check.
        :param action: The action to check.
        :return: True if the role can do the action, False otherwise.
        """
        return self.roles[role][action]

    def _add_role(self, role: ClientRole, permissions_map: Dict):
        """Add a new role."""
        if set(permissions_map.keys()) != set(ClientAction):
            raise ValueError(
                "You must provide identical permission names when add new role, "
                "did you add a new permission in the ClientAction?"
            )
        self.roles[role] = permissions_map

    @staticmethod
    def _build_role_perms() -> Dict[ClientRole, dict[ClientAction, bool]]:
        """Build the permission map for every role."""
        nobody_perms = {
            ClientAction.READ_APPLICATIONS: False,
            ClientAction.MANAGE_APPLICATIONS: False,
            ClientAction.READ_SERVICES: False,
            ClientAction.MANAGE_ACCESS_CONTROL: False,
            ClientAction.MANAGE_LIGHT_APPLICATIONS: False,
            ClientAction.READ_DB_CREDENTIAL: False,
            ClientAction.BIND_DB_SERVICE: False,
        }
        basic_reader_perms = nobody_perms | {
            ClientAction.READ_APPLICATIONS: True,
            ClientAction.READ_SERVICES: True,
        }
        basic_maintainer_perms = basic_reader_perms | {
            ClientAction.MANAGE_APPLICATIONS: True,
            ClientAction.MANAGE_ACCESS_CONTROL: True,
        }
        light_app_maintainer_perms = basic_reader_perms | {
            ClientAction.MANAGE_LIGHT_APPLICATIONS: True,
        }
        lesscode_perms = basic_maintainer_perms | {
            ClientAction.READ_DB_CREDENTIAL: True,
            ClientAction.BIND_DB_SERVICE: True,
        }

        return {
            ClientRole.NOBODY: nobody_perms,
            ClientRole.BASIC_READER: basic_reader_perms,
            ClientRole.BASIC_MAINTAINER: basic_maintainer_perms,
            ClientRole.LIGHT_APP_MAINTAINER: light_app_maintainer_perms,
            ClientRole.LESSCODE: lesscode_perms,
        }


client_perm_checker = ClientPermChecker()


def sysapi_client_perm_class(action: ClientAction) -> Type[BasePermission]:
    """Create a dynamic permission class for system API client.

    IMPORTANT: The permission class created by this function does not adhere to
    rest_framework's standard. It does not return False when the check fails;
    instead, it raises a customized APIError. This is done to provide a more
    informative error response.

    :param action: Client action type.
    :return: A permission class.
    """

    class SysAPIClientPermission(BasePermission):
        """The permission class for system API client."""

        def has_permission(self, request, view):
            sys_client = getattr(request, "sysapi_client", None)
            if not sys_client:
                raise error_codes.SYSAPI_CLIENT_NOT_FOUND
            if not client_perm_checker.role_can_do(ClientRole(sys_client.role), action):
                raise error_codes.SYSAPI_CLIENT_PERM_DENIED

            return True

    return SysAPIClientPermission


def sysapi_client_view_actions_perm(
    view_action_map: Dict[str, ClientAction], default_action: ClientAction | None = None
) -> Type[BasePermission]:
    """Create a permission class for system API view, it allows using different
    client action for different view actions.

    IMPORTANT: The permission class created by this function does not adhere to
    rest_framework's standard. It does not return False when the check fails;
    instead, it raises a customized APIError. This is done to provide a more
    informative error response.

    :param view_action_map: A map from view action to client action.
    :param default_action: Optional, the default client action if the view action
        is not found.
    :return: Permission class.
    """

    class ClientViewActionsPermission(BasePermission):
        """The permission class for system API views."""

        def has_permission(self, request, view):
            # Get the action from the view action map, if not found, use the default action.
            action = view_action_map.get(view.action, default_action)
            if not action:
                raise ValueError('No client action found for view action "%s".' % view.action)

            sys_client = getattr(request, "sysapi_client", None)
            if not sys_client:
                raise error_codes.SYSAPI_CLIENT_NOT_FOUND
            if not client_perm_checker.role_can_do(ClientRole(sys_client.role), action):
                raise error_codes.SYSAPI_CLIENT_PERM_DENIED

            return True

    return ClientViewActionsPermission
