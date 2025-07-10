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
"""Test doubles for services/addons module."""

import json
from unittest import mock

from django_dynamic_fixture import G

from paasng.accessories.servicehub.binding_policy.manager import SvcBindingPolicyManager
from paasng.accessories.servicehub.manager import mixed_service_mgr
from paasng.accessories.servicehub.services import ServiceObj
from paasng.accessories.services.models import Plan, Service, ServiceCategory, ServiceInstance
from paasng.core.tenant.user import DEFAULT_TENANT_ID
from paasng.platform.modules.models.module import Module
from tests.utils.helpers import generate_random_string


def create_local_mysql_service() -> ServiceObj:
    """Create a local MySQL service with 2 random plans."""
    service = G(Service, name="MySQL", display_name_zh_cn="MySQL", category=G(ServiceCategory), logo_b64="dummy")
    # Create some plans
    G(Plan, name=generate_random_string(), service=service)
    G(Plan, name=generate_random_string(), service=service)
    return mixed_service_mgr.get(service.uuid)


def provision_with_credentials(module: Module, service_obj: ServiceObj, credentials: dict[str, str]):
    """Bind a module with a given service and provision instances with credentials.

    **This function only supports local services.**

    :param credentials: A dictionary containing credentials for the service instance.
    """

    def _create_instance():
        """mocked function which creates a faked service instance"""
        svc = Service.objects.get(uuid=service_obj.uuid)
        return G(
            ServiceInstance,
            service=svc,
            plan=Plan.objects.filter(service=svc)[0],
            config="{}",
            credentials=json.dumps(credentials),
        )

    SvcBindingPolicyManager(service_obj, DEFAULT_TENANT_ID).set_uniform(plans=[service_obj.get_plans()[0].uuid])
    mixed_service_mgr.bind_service(service_obj, module)

    # provision service instances
    with mock.patch("paasng.accessories.services.models.Service.create_service_instance_by_plan") as mocker:
        mocker.side_effect = [_create_instance(), _create_instance()]
        for env in module.envs.all():
            for rel in mixed_service_mgr.list_unprovisioned_rels(env.engine_app):
                rel.provision()
