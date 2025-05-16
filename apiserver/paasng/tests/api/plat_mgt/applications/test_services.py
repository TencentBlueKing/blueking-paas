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
from unittest import mock

import pytest
from django.urls import reverse
from django_dynamic_fixture import G

from paasng.accessories.servicehub.binding_policy.manager import ServiceBindingPolicyManager
from paasng.accessories.servicehub.manager import mixed_service_mgr
from paasng.accessories.servicehub.models import (
    ServiceEngineAppAttachment,
)
from paasng.accessories.servicehub.sharing import ServiceSharingManager
from paasng.accessories.services.models import Plan, Service, ServiceCategory, ServiceInstance
from paasng.core.tenant.user import DEFAULT_TENANT_ID
from tests.utils.helpers import generate_random_string

pytestmark = pytest.mark.django_db


@pytest.mark.django_db(databases=["default", "workloads"])
class TestApplicationAddonServices:
    """测试应用的附加服务"""

    def _setup_services(self):
        """创建三个服务"""
        services = []
        for name in ["mysql", "redis", "mongodb"]:
            service = G(Service, name=name, category=G(ServiceCategory), logo_b64="dummy")
            G(Plan, name=generate_random_string(), service=service)
            svc_obj = mixed_service_mgr.get(service.uuid)
            services.append(svc_obj)
        return services

    def _setup_bk_app(self, app):
        """创建一个拥有复数的模块和服务的应用"""
        svc1, svc2, svc3 = self.services[0], self.services[1], self.services[2]

        module1, module2 = self.module_1, self.module_2

        # 绑定服务到模块
        for svc, module in [(svc1, module1), (svc2, module1), (svc3, module2)]:
            ServiceBindingPolicyManager(svc, DEFAULT_TENANT_ID).set_static([svc.get_plans()[0]])
            mixed_service_mgr.bind_service(svc, module)

        # 共享服务
        ServiceSharingManager(module2).create(svc1, module1)

        # # 为模块1中的所有环境分配svc1的服务实例
        # for env in module1.envs.all():
        #     for rel in mixed_service_mgr.list_unprovisioned_rels(env.engine_app, svc1):
        #         if not rel.is_provisioned():
        #             # 手动创建服务实例
        #             instance = ServiceInstance.objects.create(
        #                 service=svc1.db_object,
        #                 plan=rel.get_plan().db_object,
        #                 credentials=json.dumps(self.credentials),
        #                 config={},
        #             )
        #             # 手动分配实例到关系
        #             rel.db_obj.service_instance = instance
        #             rel.db_obj.save()

        return app

    @pytest.fixture(autouse=True)
    def setup(self, bk_app, bk_module, bk_module_2, bk_prod_env, bk_stag_env):
        """设置测试环境"""
        self.app = bk_app

        self.module_1 = bk_module
        self.stag_env = bk_stag_env
        self.prod_env = bk_prod_env

        self.module_2 = bk_module_2

        self.credentials = {"user": "test_user", "password": "test_password", "host": "127.0.0.1", "port": "3306"}

        self.services = self._setup_services()

        self._setup_bk_app(bk_app)

        svc = self.services[0]
        self.service = svc.db_object
        self.plan = svc.get_plans()[0].db_object

    def _get_service_url(self, action, **kwargs):
        """获取服务的URL"""
        return reverse(
            f"plat_mgt.applications.services.{action}",
            kwargs={
                "app_code": self.app.code,
                "module_name": self.module_1.name,
                "service_id": str(self.service.uuid),
                "env_name": self.stag_env.environment,
                **kwargs,
            },
        )

    def create_service_instance(self, credentials=None):
        """创建服务实例"""
        if credentials is None:
            credentials = self.credentials

        return ServiceInstance.objects.create(
            service=self.service,
            plan=self.plan,
            credentials=json.dumps(credentials),
            config={},
        )

    def create_attachment(self, service_instance=None):
        """创建或更新服务附件"""

        return ServiceEngineAppAttachment.objects.update_or_create(
            engine_app=self.stag_env.engine_app,
            service=self.service,
            defaults={
                "plan": self.plan,
                "service_instance": service_instance,
            },
        )

    def test_list(self, plat_mgt_api_client):
        """测试获取应用的附加服务列表"""
        url = reverse("plat_mgt.applications.services", kwargs={"app_code": self.app.code})
        resp = plat_mgt_api_client.get(url)
        assert resp.status_code == 200
        assert isinstance(resp.data, list)
        print("数据: ", resp.data)
        assert len(resp.data) > 0

    def test_assign_instance(self, plat_mgt_api_client):
        """测试分配附加服务实例"""

        ServiceEngineAppAttachment.objects.filter(engine_app=self.stag_env.engine_app, service=self.service).delete()
        attachment, _ = self.create_attachment(None)

        # 构造API请求URL
        url = self._get_service_url("assign_instance")

        instance = self.create_service_instance()

        with mock.patch.object(Service, "create_service_instance_by_plan", return_value=instance):
            rsp = plat_mgt_api_client.post(url)
            assert rsp.status_code == 201

            # 验证附件现在关联了服务实例
            attachment.refresh_from_db()
            assert attachment.service_instance is not None

    def test_delete_instance(self, plat_mgt_api_client):
        """测试删除附加服务实例"""

        # 创建服务实例和关联
        instance = self.create_service_instance()
        attachment, _ = self.create_attachment(instance)

        # 构造API请求URL
        url = self._get_service_url("delete_instance", instance_id=str(instance.uuid))

        rsp = plat_mgt_api_client.delete(url)
        assert rsp.status_code == 204

        # 验证实例已解除关联
        attachment.refresh_from_db()
        assert attachment.service_instance is None

    def test_view_credentials(self, plat_mgt_api_client):
        """测试查看附加服务实例的凭据"""

        # 创建服务实例和关联
        instance = self.create_service_instance()
        self.create_attachment(instance)

        # 构造API请求URL
        url = self._get_service_url("view_credentials", instance_id=str(instance.uuid))

        rsp = plat_mgt_api_client.get(url)
        assert rsp.status_code == 200
        assert rsp.data["result"] == self.credentials
