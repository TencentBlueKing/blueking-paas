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
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from paasng.accessories.servicehub.constants import ServiceType
from paasng.accessories.servicehub.models import (
    ServiceEngineAppAttachment,
    ServiceModuleAttachment,
    SharedServiceAttachment,
)
from paasng.accessories.services.models import Plan, Service, ServiceCategory, ServiceInstance
from paasng.platform.modules.models.module import Module
from tests.utils.helpers import generate_random_string, initialize_module

pytestmark = pytest.mark.django_db


@pytest.fixture
def test_credentials():
    """返回用于测试的凭据"""
    return {"user": "test_user", "password": "test_password", "host": "127.0.0.1", "port": "3306"}


@pytest.fixture
def services_obj(db):
    """创建两个本地增强服务"""
    # 创建服务分类
    category = ServiceCategory.objects.create(name_en="test_category")
    temp_logo1 = SimpleUploadedFile("test_logo.png", b"\x00\x01\x02\x03", content_type="image/png")
    temp_logo2 = SimpleUploadedFile("test_logo.png", b"\x00\x01\x02\x03", content_type="image/png")

    # 创建两个服务
    service1 = Service.objects.create(
        name="test_service1",
        logo=temp_logo1,
        category=category,
        config={"provider_name": "mysql"},
        is_active=True,
        is_visible=True,
    )

    service2 = Service.objects.create(
        name="test_service2",
        logo=temp_logo2,
        category=category,
        config={"provider_name": "redis"},
        is_active=True,
        is_visible=True,
    )

    return service1, service2


@pytest.fixture
def bk_app_with_modules_services(bk_app, services_obj, test_credentials):
    """将两个模块和两个服务组合在一起"""
    service1, service2 = services_obj

    # 创建第二个模块
    module2 = Module.objects.create(
        application=bk_app,
        name=generate_random_string(length=8),
        language="python",
        creator=bk_app.creator,
    )
    initialize_module(module2)

    modules = list(bk_app.modules.all())
    module1, module2 = modules[0], modules[1]

    # 绑定服务
    attachment1 = ServiceModuleAttachment.objects.create(module=module1, service=service1)
    attachment2 = ServiceModuleAttachment.objects.create(module=module1, service=service2)

    # 共享服务
    SharedServiceAttachment.objects.create(
        module=module2,
        service_id=service1.pk,
        service_type=ServiceType.LOCAL,
        ref_attachment_pk=attachment1.pk,
    )
    SharedServiceAttachment.objects.create(
        module=module2,
        service_id=service2.pk,
        service_type=ServiceType.LOCAL,
        ref_attachment_pk=attachment2.pk,
    )

    # 确保每个模块的环境都有 ServiceEngineAppAttachment
    from paasng.accessories.services.models import Plan

    # 创建服务计划和引擎应用关联
    plan1 = Plan.objects.create(service=service1, name="default-plan-1", is_active=True)
    plan2 = Plan.objects.create(service=service2, name="default-plan-2", is_active=True)

    # 为每个模块的每个环境创建服务绑定
    for module in [module1, module2]:
        for env in module.envs.all():
            ServiceEngineAppAttachment.objects.create(
                engine_app=env.engine_app,
                service=service1,
                plan=plan1,
            )
            ServiceEngineAppAttachment.objects.create(
                engine_app=env.engine_app,
                service=service2,
                plan=plan2,
            )

    # 为第一个模块的第一个环境创建服务实例
    env = module1.envs.first()
    service_instance = ServiceInstance.objects.create(
        service=service1,
        plan=plan1,
        credentials=json.dumps(test_credentials),
        config={},
    )

    # 更新服务与环境的关联，添加实例
    attachment = ServiceEngineAppAttachment.objects.get(engine_app=env.engine_app, service=service1)
    attachment.service_instance = service_instance
    attachment.save()

    return bk_app


@pytest.mark.django_db(databases=["default", "workloads"])
class TestApplicationAddonServices:
    """测试应用的附加服务"""

    @pytest.fixture(autouse=True)
    def setup(self, bk_app_with_modules_services, services_obj):
        """设置测试环境"""
        self.app = bk_app_with_modules_services
        self.module = list(self.app.modules.all())[0]  # 使用第一个模块
        self.env = self.module.envs.first()  # 获取第一个环境
        self.service = services_obj[0]
        self.plan = Plan.objects.get(service=self.service)

    def create_service_instance(self, credentials):
        """创建服务实例"""
        return ServiceInstance.objects.create(
            service=self.service,
            plan=self.plan,
            credentials=json.dumps(credentials),
            config={},
        )

    def test_list(self, plat_mgt_api_client):
        """测试获取应用的附加服务列表"""
        url = reverse("plat_mgt.applications.services", kwargs={"app_code": self.app.code})
        resp = plat_mgt_api_client.get(url)
        assert resp.status_code == 200
        assert isinstance(resp.data, list)
        assert len(resp.data) > 0

    def test_assign_instance(self, plat_mgt_api_client, test_credentials):
        """测试分配附加服务实例"""

        # 准备未分配实例的关系
        ServiceEngineAppAttachment.objects.filter(engine_app=self.env.engine_app, service=self.service).delete()
        attachment = ServiceEngineAppAttachment.objects.create(
            engine_app=self.env.engine_app, service=self.service, plan=self.plan, service_instance=None
        )

        # 创建一个服务实例
        instance = self.create_service_instance(test_credentials)

        url = reverse(
            "plat_mgt.applications.services.assign_instance",
            kwargs={
                "app_code": self.app.code,
                "module_name": self.module.name,
                "env_name": self.env.environment,
                "service_id": str(self.service.uuid),
            },
        )

        with mock.patch.object(Service, "create_service_instance_by_plan", return_value=instance):
            rsp = plat_mgt_api_client.post(url)
            assert rsp.status_code == 201

            # 验证实例是否被分配 - 从数据库重新查询
            attachment.refresh_from_db()
            assert attachment.service_instance is not None
            assert hasattr(attachment.service_instance, "credentials")

    def test_delete_instance(self, plat_mgt_api_client, test_credentials):
        """测试删除附加服务实例"""

        # 创建服务实例和关联
        instance = self.create_service_instance(test_credentials)
        attachment, _ = ServiceEngineAppAttachment.objects.update_or_create(
            engine_app=self.env.engine_app,
            service=self.service,
            defaults={"plan": self.plan, "service_instance": instance},
        )

        # 确认已关联
        assert attachment.service_instance is not None

        # 构造API请求URL
        url = reverse(
            "plat_mgt.applications.services.delete_instance",
            kwargs={
                "app_code": self.app.code,
                "module_name": self.module.name,
                "env_name": self.env.environment,
                "service_id": str(self.service.uuid),
                "instance_id": str(instance.uuid),
            },
        )

        rsp = plat_mgt_api_client.delete(url)
        assert rsp.status_code == 204

        # 验证实例已解除关联
        attachment.refresh_from_db()
        assert attachment.service_instance is None

    def test_view_credentials(self, plat_mgt_api_client, test_credentials):
        """测试查看附加服务实例的凭据"""

        # 创建服务实例和关联
        instance = self.create_service_instance(test_credentials)
        ServiceEngineAppAttachment.objects.update_or_create(
            engine_app=self.env.engine_app,
            service=self.service,
            defaults={"plan": self.plan, "service_instance": instance},
        )

        # 构造API请求URL
        url = reverse(
            "plat_mgt.applications.services.view_credentials",
            kwargs={
                "app_code": self.app.code,
                "module_name": self.module.name,
                "env_name": self.env.environment,
                "service_id": str(self.service.uuid),
                "instance_id": str(instance.uuid),
            },
        )

        rsp = plat_mgt_api_client.get(url)
        assert rsp.status_code == 200
        assert "result" in rsp.data
        assert rsp.data["result"] == test_credentials
