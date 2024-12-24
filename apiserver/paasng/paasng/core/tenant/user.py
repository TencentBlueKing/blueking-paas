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


from attrs import define
from bkpaas_auth.models import User
from django.conf import settings

# The default tenant id exists only if the project does not enable multi-tenant mode,
# it serves as a reserved value. When multi-tenant mode is enabled, no tenant id can
# be "default".
DEFAULT_TENANT_ID = "default"

# The operation tenant id, when the user belongs to this tenant, some special actions
# can be performed.
OP_TYPE_TENANT_ID = "system"


@define
class Tenant:
    """A simple tenant type.

    :param id: The tenant's id.
    :param is_op_type: Whether the tenant is an operation tenant, an operation
        tenant is special and users in that tenant can perform special actions.
    :param is_stub: When the project does not enable "multi-tenant" mode, this field
        is set to True to indicate that the tenant is only a stub tenant.
    """

    id: str
    is_op_type: bool = False
    is_stub: bool = False

    def __attrs_post_init__(self):
        self.is_op_type = self.id == OP_TYPE_TENANT_ID
        if self.id == DEFAULT_TENANT_ID and not self.is_stub:
            raise ValueError("Invalid tenant id")


def get_tenant(user: User) -> Tenant:
    """Get the user's tenant.

    :raise ValueError: If the tenant cannot be found.
    """
    if not settings.ENABLE_MULTI_TENANT_MODE:
        return Tenant(id=DEFAULT_TENANT_ID, is_stub=True)

    # TODO: Get the tenant info directly from the user object when bkpaas_auth is ready
    try:
        _id = getattr(user, "tenant_id")
    except AttributeError:
        raise ValueError("No tenant can be found")
    return Tenant(_id)


def set_tenant(user: User, tenant_id: str):
    """Set the tenant info for the user. This function is only useful for running
    test cases, in real world scenarios, the tenant info should be set by the auth
    middleware.
    """
    user.tenant_id = tenant_id
