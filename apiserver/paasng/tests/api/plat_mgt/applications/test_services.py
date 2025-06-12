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


import json
import uuid
from unittest import mock

import pytest
from django_dynamic_fixture import G

from paasng.accessories.servicehub.binding_policy.manager import SvcBindingPolicyManager
from paasng.accessories.servicehub.exceptions import UnboundSvcAttachmentDoesNotExist
from paasng.accessories.servicehub.manager import mixed_service_mgr
from paasng.accessories.servicehub.sharing import ServiceSharingManager
from paasng.accessories.services.models import Plan, PreCreatedInstance, Service, ServiceCategory
from paasng.core.tenant.user import DEFAULT_TENANT_ID
from paasng.utils.error_codes import error_codes
from tests.utils.helpers import generate_random_string

pytestmark = pytest.mark.django_db


@pytest.mark.django_db(databases=["default", "workloads"])
class TestApplicationServicesViewSet:
    """测试应用的增强服务"""

    @pytest.fixture(autouse=True)
    def setup_services(self, bk_app, bk_module, bk_module_2, bk_stag_env, bk_prod_env):
        """创建服务和绑定关系"""
        self.app = bk_app
        self.module_1 = bk_module
        self.module_2 = bk_module_2
        self.stag_env = bk_stag_env
        self.prod_env = bk_prod_env

        # 创建测试凭证
        self.credentials = {
            "user": "test_user",
            "password": "test_password",
            "host": "127.0.0.1",
            "port": "3306",
        }

        # 创建三个服务
        services = []
        for name in ["mysql", "redis", "mongodb"]:
            service = G(
                Service,
                name=name,
                category=G(ServiceCategory),
                logo_b64="dummy",
                config={"provider_name": "pool"},
            )
            plan = G(
                Plan,
                name=generate_random_string(),
                service=service,
                config=json.dumps({}),
            )
            # 为每个服务创建预创建服务实例
            G(
                PreCreatedInstance,
                plan=plan,
                is_allocated=False,
                credentials=json.dumps(self.credentials),
                config={},
            )

            svc = mixed_service_mgr.get(service.uuid)
            services.append(svc)

        # 绑定服务到模块
        svc1, svc2, svc3 = services
        for svc, module in [(svc1, bk_module), (svc2, bk_module), (svc3, bk_module_2)]:
            SvcBindingPolicyManager(svc, DEFAULT_TENANT_ID).set_uniform(plans=[svc.get_plans()[0].uuid])
            mixed_service_mgr.bind_service(svc, module)

        # 共享服务
        ServiceSharingManager(bk_module_2).create(svc1, bk_module)

        # 保存服务供测试使用
        self.services = services
        self.svc = services[0]
        self.plan = self.svc.get_plans()[0]

    def test_list_bound_attachments(self, plat_mgt_api_client):
        """测试获取应用的绑定服务列表"""
        url = f"/api/plat_mgt/applications/{self.app.code}/services/bound_attachments/"
        resp = plat_mgt_api_client.get(url)
        assert resp.status_code == 200
        assert isinstance(resp.data, list)
        assert len(resp.data) > 0

    def test_list_unbound_attachments(self, plat_mgt_api_client):
        """测试获取可回收的实例列表"""

        # 创建一个服务实例并解绑
        rel = next(mixed_service_mgr.list_unprovisioned_rels(self.stag_env.engine_app, service=self.svc), None)
        assert rel is not None
        rel.provision()
        rel.recycle_resource()

        url = f"/api/plat_mgt/applications/{self.app.code}/services/unbound_attachments/"
        resp = plat_mgt_api_client.get(url)

        assert resp.status_code == 200
        assert len(resp.data) > 0

    @mock.patch("paasng.plat_mgt.applications.views.services.add_admin_audit_record", return_value=None)
    def test_provision_instance(self, mock_audit_record, plat_mgt_api_client):
        """测试分配服务实例"""

        # 构造API请求URL
        url = f"/api/plat_mgt/applications/{self.app.code}/modules/{self.module_1.name}/envs/{self.stag_env.environment}/services/{self.svc.uuid}/instance/"
        rsp = plat_mgt_api_client.post(url)
        assert rsp.status_code == 201

        # 验证已经分配了实例
        service_rel = mixed_service_mgr.get_attachment_by_engine_app(self.svc, self.stag_env.engine_app)
        assert service_rel.service_instance is not None

        # 验证审计记录函数被调用
        mock_audit_record.assert_called_once()

    def test_provision_shared_service_instance_forbidden(self, plat_mgt_api_client):
        """测试创建共享服务实例"""

        # 构造API请求URL, 这里使用 module_2，因为它是共享服务的目标模块
        url = f"/api/plat_mgt/applications/{self.app.code}/modules/{self.module_2.name}/envs/{self.stag_env.environment}/services/{self.svc.uuid}/instance/"

        # 模拟共享服务的创建
        resp = plat_mgt_api_client.post(url)

        assert resp.status_code == 400
        assert resp.data["code"] == error_codes.CANNOT_PROVISION_INSTANCE.code

    def test_unbound_instance(self, plat_mgt_api_client):
        """测试解绑增强服务实例"""

        # 创建服务实例和关联
        rel = next(mixed_service_mgr.list_unprovisioned_rels(self.stag_env.engine_app, self.svc), None)
        assert rel is not None
        rel.provision()
        instance_uuid = rel.get_instance().uuid

        # 构造API请求URL
        url = f"/api/plat_mgt/applications/{self.app.code}/modules/{self.module_1.name}/envs/{self.stag_env.environment}/services/{self.svc.uuid}/instance/{instance_uuid}/"
        rsp = plat_mgt_api_client.delete(url)
        assert rsp.status_code == 204

        # 验证实例已解除关联
        unbound_rel = mixed_service_mgr.get_unbound_instance_rel_by_instance_id(self.svc, uuid.UUID(instance_uuid))
        assert unbound_rel is not None

    def test_unbound_shared_service_instance_forbidden(self, plat_mgt_api_client):
        # 创建服务实例和关联, 使用 module_1
        rel = next(mixed_service_mgr.list_unprovisioned_rels(self.stag_env.engine_app, self.svc), None)
        assert rel is not None
        rel.provision()
        instance_uuid = rel.get_instance().uuid

        # 构造API请求URL, 这里使用 module_2，因为它是共享服务的目标模块
        url = f"/api/plat_mgt/applications/{self.app.code}/modules/{self.module_2.name}/envs/{self.stag_env.environment}/services/{self.svc.uuid}/instance/{instance_uuid}/"
        resp = plat_mgt_api_client.delete(url)

        assert resp.status_code == 400
        assert resp.data["code"] == error_codes.CANNOT_DESTROY_SERVICE.code

    def test_recycle_unbound_instance(self, plat_mgt_api_client):
        """测试回收已解绑的服务资源"""

        # 创建一个服务实例
        rel = next(mixed_service_mgr.list_unprovisioned_rels(self.stag_env.engine_app, service=self.svc), None)
        assert rel is not None
        rel.provision()

        # 获取实例ID并解绑
        instance_uuid = uuid.UUID(rel.get_instance().uuid)
        rel.recycle_resource()

        # 确认实例已解绑成功
        unbound_rel = mixed_service_mgr.get_unbound_instance_rel_by_instance_id(self.svc, instance_uuid)
        assert unbound_rel is not None

        url = f"/api/plat_mgt/applications/{self.app.code}/services/{self.svc.uuid}/instance/{instance_uuid}/"
        resp = plat_mgt_api_client.delete(url)

        # 验证 API 调用成功且实例已经回收
        assert resp.status_code == 204
        with pytest.raises(UnboundSvcAttachmentDoesNotExist):
            mixed_service_mgr.get_unbound_instance_rel_by_instance_id(self.svc, instance_uuid)

    def test_view_credentials(self, plat_mgt_api_client):
        """测试查看附加服务实例的凭据"""

        # 创建服务实例和关联
        rel = next(mixed_service_mgr.list_unprovisioned_rels(self.stag_env.engine_app, self.svc), None)
        assert rel is not None
        rel.provision()

        instance_uuid = rel.get_instance().uuid

        # 构造API请求URL
        url = f"/api/plat_mgt/applications/{self.app.code}/modules/{self.module_1.name}/envs/{self.stag_env.environment}/services/{self.svc.uuid}/instance/{instance_uuid}/credentials/"
        rsp = plat_mgt_api_client.get(url)
        assert rsp.status_code == 200

        # 验证返回的凭据与创建时一致
        assert len(rsp.data) > 0
