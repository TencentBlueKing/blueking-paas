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

from typing import Dict

import pytest
from blue_krill.contextlib import nullcontext as does_not_raise
from django.conf import settings
from django.utils.translation import override
from django_dynamic_fixture import G

from paasng.accessories.publish.market.models import Product, Tag
from paasng.accessories.servicehub.binding_policy.manager import SvcBindingPolicyManager
from paasng.accessories.servicehub.constants import Category
from paasng.accessories.servicehub.manager import mixed_service_mgr
from paasng.accessories.servicehub.sharing import ServiceSharingManager
from paasng.accessories.services.models import Plan, Service, ServiceCategory
from paasng.core.region.models import get_all_regions
from paasng.core.tenant.constants import AppTenantMode
from paasng.core.tenant.utils import AppTenantInfo
from paasng.platform.applications.models import Application
from paasng.platform.declarative.application.constants import CNATIVE_APP_CODE_FIELD
from paasng.platform.declarative.application.controller import AppDeclarativeController
from paasng.platform.declarative.application.resources import ApplicationDesc, get_application
from paasng.platform.declarative.application.validations.v3 import AppDescriptionSLZ
from paasng.platform.declarative.exceptions import DescriptionValidationError
from paasng.platform.declarative.serializers import validate_desc
from tests.paasng.platform.declarative.utils import AppDescV3Builder as builder  # noqa: N813
from tests.paasng.platform.declarative.utils import AppDescV3Decorator as decorator  # noqa: N813
from tests.utils.auth import create_user
from tests.utils.basic import generate_random_string
from tests.utils.helpers import configure_regions, create_app

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


def get_app_description(app_json: Dict) -> ApplicationDesc:
    """A help tool get parse the application json data, describe at app_desc.yml::app to ApplicationDesc"""
    instance = get_application(app_json, CNATIVE_APP_CODE_FIELD)
    desc = validate_desc(AppDescriptionSLZ, app_json, instance=instance)
    return desc


@pytest.fixture(autouse=True)
def tag(bk_app):
    """A tag fixture for testing"""
    parent = Tag.objects.create(name="parent test")
    return Tag.objects.create(name="test", parent=parent)


@pytest.fixture(autouse=True)
def app_tenant():
    """Fixture providing tenant information for application creation"""
    return AppTenantInfo(app_tenant_mode=AppTenantMode.GLOBAL, app_tenant_id="", tenant_id="default")


@pytest.fixture(autouse=True)
def declarative_controller(bk_user, app_tenant):
    return AppDeclarativeController(
        user=bk_user,
        app_tenant_conf=app_tenant,
    )


class TestAppDeclarativeControllerCreation:
    @pytest.mark.parametrize("field_name", ["bkAppCode", "bkAppName", "region"])
    def test_run_invalid_input(self, random_name, field_name, declarative_controller):
        app_json = {"bkAppCode": random_name, "bkAppName": random_name}
        app_json[field_name] = "@invalid value" * 10

        with pytest.raises(DescriptionValidationError) as exc_info:
            declarative_controller.perform_action(get_app_description(app_json))
        assert field_name in exc_info.value.detail

    @pytest.mark.parametrize(
        ("bk_app_code_len", "ctx"),
        [
            (16, does_not_raise()),
            (20, does_not_raise()),
            (21, pytest.raises(DescriptionValidationError)),
            (30, pytest.raises(DescriptionValidationError)),
        ],
    )
    def test_app_code_length(self, bk_app_code_len, ctx, declarative_controller):
        # 保证应用 ID 是以字母开头
        bk_app_code = f"ut{generate_random_string(length=(bk_app_code_len - 2))}"
        app_json = builder.make_app_desc(bk_app_code, decorator.with_module("default", True))

        with ctx:
            declarative_controller.perform_action(get_app_description(app_json))

    def test_name_is_duplicated(self, random_name, declarative_controller):
        existed_app = create_app()
        app_json = {
            "bkAppCode": random_name,
            "bkAppName": existed_app.name,
        }
        with pytest.raises(DescriptionValidationError) as exc_info:
            declarative_controller.perform_action(get_app_description(app_json))
        assert "bkAppName" in exc_info.value.detail

    @pytest.mark.parametrize("module_name", ["$", "0us0", "-a", "a-", "_a", "a_", "a0us0b"])
    def test_invalid_module_name(self, module_name, random_name):
        app_json = builder.make_app_desc(random_name, decorator.with_module(module_name=module_name, is_default=True))
        with pytest.raises(DescriptionValidationError):
            get_app_description(app_json)

    @pytest.mark.parametrize(
        ("region", "has_error"),
        [
            (None, False),
            ("r1", False),
            # nondefault region is not supported and should raise an error
            ("r2", True),
        ],
    )
    @pytest.mark.usefixtures("mock_wl_services_in_creation")
    def test_region_perm_check(self, bk_user, random_name, region, has_error, declarative_controller):
        with configure_regions(["r1", "r2"]):
            app_json = builder.make_app_desc(
                random_name,
                decorator.with_module("default", True),
                *([decorator.with_region(region)] if region is not None else []),
            )
            if has_error:
                with pytest.raises(DescriptionValidationError) as exc_info:
                    declarative_controller.perform_action(get_app_description(app_json))
                assert "region" in exc_info.value.detail
            else:
                declarative_controller.perform_action(get_app_description(app_json))

    def test_normal(self, random_name, declarative_controller, app_tenant):
        app_json = builder.make_app_desc(random_name, decorator.with_module("default", True))
        application = declarative_controller.perform_action(get_app_description(app_json))
        assert application.tenant_id == app_tenant.tenant_id
        assert application.app_tenant_id == app_tenant.app_tenant_id
        assert application.app_tenant_mode == app_tenant.app_tenant_mode

        default_module = application.get_default_module()
        assert default_module.tenant_id == app_tenant.tenant_id

    def test_i18n(self, random_name, declarative_controller):
        app_json = builder.make_app_desc(
            random_name,
            decorator.with_module("default", True),
            decorator.with_market(
                introduction="介绍", description="描述", introduction_en="introduction", description_en="description"
            ),
        )
        application = declarative_controller.perform_action(get_app_description(app_json))
        with override("zh-cn"):
            assert application.get_product().introduction == "介绍"
            assert application.get_product().description == "描述"
        with override("en"):
            assert application.get_product().introduction == "introduction"
            assert application.get_product().description == "description"


class TestAppDeclarativeControllerUpdate:
    @pytest.fixture()
    def existed_app(self, random_name, declarative_controller):
        """Create an application before to test update"""
        app_json = builder.make_app_desc(
            random_name,
            decorator.with_module("default", True),
        )
        declarative_controller.perform_action(get_app_description(app_json))
        return Application.objects.get(code=random_name)

    def test_without_permission(self, bk_user, existed_app, app_tenant):
        another_user = create_user(username="another_user")
        app_json = builder.make_app_desc(
            existed_app.code,
            decorator.with_module("default", True),
        )

        controller = AppDeclarativeController(another_user, app_tenant)
        with pytest.raises(DescriptionValidationError) as exc_info:
            controller.perform_action(get_app_description(app_json))
        assert "bk_app_code" in exc_info.value.detail

    def test_region_modified(self, existed_app, declarative_controller):
        # Get a different and valid region
        regions = get_all_regions().keys()
        diff_region = [r for r in regions if r != existed_app.region][0]

        # Use new region
        app_json = builder.make_app_desc(
            existed_app.code,
            decorator.with_module("default", True),
        )
        app_json["bkAppName"] = existed_app.name
        app_json["region"] = diff_region
        with pytest.raises(DescriptionValidationError) as exc_info:
            declarative_controller.perform_action(get_app_description(app_json))
        assert "region" in exc_info.value.detail

    def test_name_not_modified(self, existed_app, declarative_controller):
        # Use new name
        new_name = existed_app.name + "2"
        new_name_en = existed_app.name + "en"

        app_json = builder.make_app_desc(
            existed_app.code,
            decorator.with_module("default", True),
        )
        app_json["bkAppName"] = new_name
        app_json["bkAppNameEn"] = new_name_en

        application = declarative_controller.perform_action(get_app_description(app_json))
        application.refresh_from_db()
        assert application.name == existed_app.name
        assert application.name_en == existed_app.name

    def test_normal(self, existed_app, declarative_controller):
        app_json = builder.make_app_desc(
            existed_app.code,
            decorator.with_module("default", True),
        )
        app_json["bkAppName"] = existed_app.name

        declarative_controller.perform_action(get_app_description(app_json))


class TestMarketField:
    def test_creation(self, bk_user, random_name, tag, declarative_controller, app_tenant):
        app_desc = builder.make_app_desc(
            random_name,
            decorator.with_module("default", True),
            decorator.with_market(introduction=random_name, tag=tag),
        )
        declarative_controller.perform_action(get_app_description(app_desc))

        product = Product.objects.get(code=random_name)
        assert product.tag == tag
        assert product.introduction == random_name
        assert product.tenant_id == app_tenant.tenant_id


class TestMarketDisplayOptionsField:
    def test_creation_omitted(self, random_name, app_tenant, declarative_controller):
        minimal_app_desc = builder.make_app_desc(
            random_name, decorator.with_module("default", True), decorator.with_market(introduction=random_name)
        )
        declarative_controller.perform_action(get_app_description(minimal_app_desc))

        product = Product.objects.get(code=random_name)
        assert product.tag is None
        assert product.introduction == random_name
        assert product.displayoptions.width == 1280
        assert product.displayoptions.height == 600
        assert product.displayoptions.is_win_maximize is False
        assert product.displayoptions.visible is True
        assert product.displayoptions.open_mode == "new_tab"
        assert product.tenant_id == app_tenant.tenant_id


class TestServicesField:
    @pytest.fixture(autouse=True)
    def _default_services(self, request, app_tenant):
        """Create local services in order by run unit tests"""
        category = G(ServiceCategory, id=Category.DATA_STORAGE)
        service_names = ["mysql", "rabbitmq"]
        for name in service_names:
            # Create service object
            svc = G(Service, name=name, category=category, logo_b64="dummy")
            # Create default plans
            G(Plan, name="plan-1", service=svc, config="{}", is_active=True)
            G(Plan, name="plan-2", service=svc, config="{}", is_active=True)

            # Create a default binding polity so that the binding works by default
            service = mixed_service_mgr.get(svc.uuid)
            SvcBindingPolicyManager(service, app_tenant.tenant_id).set_uniform(plans=[service.get_plans()[0].uuid])

    @pytest.fixture()
    def app_desc(self, random_name, tag):
        return builder.make_app_desc(
            random_name,
            decorator.with_market(
                introduction="应用简介",
                display_options={"open_mode": "desktop"},
            ),
            decorator.with_module(
                module_name=random_name,
                is_default=True,
                module_spec={"addons": [{"name": "mysql"}], "processes": []},
            ),
        )

    def test_creation(self, random_name, app_desc, declarative_controller):
        declarative_controller.perform_action(get_app_description(app_desc))

        service_obj = mixed_service_mgr.find_by_name("mysql")
        application = Application.objects.get(code=random_name)
        assert mixed_service_mgr.module_is_bound_with(service_obj, application.get_default_module()) is True

    def test_update_add(self, random_name, app_desc, declarative_controller):
        declarative_controller.perform_action(get_app_description(app_desc))

        # Add a new service
        service_obj = mixed_service_mgr.find_by_name("rabbitmq")
        module = Application.objects.get(code=random_name).get_default_module()

        assert mixed_service_mgr.module_is_bound_with(service_obj, module) is False
        app_desc["modules"][0]["spec"]["addons"].append({"name": service_obj.name})
        declarative_controller.perform_action(get_app_description(app_desc))
        assert mixed_service_mgr.module_is_bound_with(service_obj, module) is True

    def test_not_existed_service(self, random_name, app_desc, declarative_controller):
        app_desc["modules"][0]["spec"]["addons"] = [{"name": "invalid-service"}]

        declarative_controller.perform_action(get_app_description(app_desc))

        application = Application.objects.get(code=random_name)
        services = mixed_service_mgr.list_binded(application.get_default_module())
        assert len(list(services)) == 0

    def test_shared_service(self, random_name, app_desc, declarative_controller):
        decorator.with_module(
            random_name + "1",
            is_default=False,
            module_spec={"addons": [{"name": "mysql", "sharedFromModule": random_name}], "processes": []},
        )(app_desc)

        declarative_controller.perform_action(get_app_description(app_desc))

        service_obj = mixed_service_mgr.find_by_name("mysql", settings.DEFAULT_REGION_NAME)
        application = Application.objects.get(code=random_name)
        module = application.get_module(random_name + "1")
        ref_module = application.get_module(random_name)
        info = ServiceSharingManager(module).get_shared_info(service_obj)
        assert info is not None
        assert info.ref_module == ref_module
        assert info.module == module

    def test_shared_service_but_module_not_found(self, random_name, app_desc):
        decorator.with_module(
            random_name + "1",
            is_default=False,
            module_spec={"addons": [{"name": "mysql", "sharedFromModule": random_name + "2"}], "processes": []},
        )(app_desc)
        with pytest.raises(DescriptionValidationError):
            get_app_description(app_desc)
