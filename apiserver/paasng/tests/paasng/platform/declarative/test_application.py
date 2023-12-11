# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except
in compliance with the License. You may obtain a copy of the License at

    http://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software distributed under
the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the specific language governing permissions and
limitations under the License.

We undertake not to change the open source license (MIT license) applicable
to the current version of the project delivered to anyone in the future.
"""
from typing import Any, Dict, List, Optional

import pytest
from django.conf import settings
from django.utils.translation import override
from django_dynamic_fixture import G

from paasng.accessories.publish.market.models import Product, Tag
from paasng.accessories.servicehub.constants import Category
from paasng.accessories.servicehub.manager import mixed_service_mgr
from paasng.accessories.servicehub.sharing import ServiceSharingManager
from paasng.accessories.services.models import Plan, Service, ServiceCategory
from paasng.core.region.models import get_all_regions
from paasng.infras.accounts.models import UserProfile
from paasng.platform.applications.models import Application
from paasng.platform.declarative.application.controller import APP_CODE_FIELD, AppDeclarativeController
from paasng.platform.declarative.application.resources import ApplicationDesc, get_application
from paasng.platform.declarative.application.validations import AppDescriptionSLZ
from paasng.platform.declarative.exceptions import DescriptionValidationError
from paasng.platform.declarative.serializers import validate_desc
from tests.utils.auth import create_user
from tests.utils.helpers import configure_regions, create_app, generate_random_string

pytestmark = pytest.mark.django_db


def get_app_description(app_json: Dict) -> ApplicationDesc:
    """A help tool get parse the application json data, describe at app_desc.yml::app to ApplicationDesc"""
    instance = get_application(app_json, APP_CODE_FIELD)
    desc = validate_desc(AppDescriptionSLZ, app_json, instance=instance)
    return desc


@pytest.fixture(autouse=True)
def tag(bk_app):
    """A tag fixture for testing"""
    parent = Tag.objects.create(name="parent test", region=bk_app.region)
    return Tag.objects.create(name="test", region=bk_app.region, parent=parent)


def make_app_desc(
    random_name,
    *,
    region: Optional[str] = None,
    introduction: Optional[str] = None,
    display_options: Optional[Dict] = None,
    tag: Optional[Tag] = None,
    description: Optional[str] = None,
    services: Optional[List] = None,
) -> Dict[str, Any]:
    """Make description data for testing"""
    result: Dict[str, Any] = {
        "region": region,
        "bk_app_code": random_name,
        "bk_app_name": random_name,
        "market": {
            "introduction": introduction or random_name,
            "introduction_en": (introduction or random_name)[::-1],
        },
        "modules": {random_name: {"is_default": True, "language": "python"}},
    }
    if display_options is not None:
        result["market"]["display_options"] = display_options
    if tag is not None:
        result["market"]["category"] = tag.name
    if description is not None:
        result["market"]["description"] = description
        result["market"]["description_en"] = description[::-1]
    if services is not None:
        result["modules"][random_name]["services"] = services
    return result


class TestAppDeclarativeControllerCreation:
    @pytest.mark.parametrize("field_name", ["bk_app_code", "bk_app_name", "region"])
    def test_run_invalid_input(self, bk_user, random_name, field_name):
        app_json = {"bk_app_code": random_name, "bk_app_name": random_name}
        app_json[field_name] = "@invalid value" * 10

        controller = AppDeclarativeController(bk_user)
        with pytest.raises(DescriptionValidationError) as exc_info:
            controller.perform_action(get_app_description(app_json))
        assert field_name in exc_info.value.detail

    @pytest.mark.parametrize(("bk_app_code_len", "is_valid"), [(16, True), (20, False), (30, False)])
    def test_app_code_length(self, bk_user, random_name, bk_app_code_len, is_valid):
        # 保证应用 ID 是以字母开头
        bk_app_code = f"ut{generate_random_string(length=(bk_app_code_len-2))}"
        app_json = make_app_desc(bk_app_code)

        controller = AppDeclarativeController(bk_user)
        if is_valid:
            controller.perform_action(get_app_description(app_json))
        else:
            with pytest.raises(DescriptionValidationError):
                controller.perform_action(get_app_description(app_json))

    def test_name_is_duplicated(self, bk_user, random_name):
        existed_app = create_app()
        app_json = {
            "bk_app_code": random_name,
            "bk_app_name": existed_app.name,
        }
        with pytest.raises(DescriptionValidationError) as exc_info:
            AppDeclarativeController(bk_user).perform_action(get_app_description(app_json))
        assert "bk_app_name" in exc_info.value.detail

    @pytest.mark.parametrize("module_name", ["$", "0us0", "-a", "a-", "_a", "a_", "a0us0b"])
    def test_invalid_module_name(self, module_name, random_name):
        app_json = {
            "bk_app_code": random_name,
            "bk_app_name": random_name,
            "modules": {module_name: {"is_default": True, "language": "python"}},
        }
        with pytest.raises(DescriptionValidationError):
            get_app_description(app_json)

    @pytest.mark.parametrize(
        ("profile_regions", "region", "is_success"),
        [
            (["r1"], "r1", True),
            (["r1"], "r2", False),
            (["r1"], None, True),
        ],
    )
    def test_region_perm_check(self, bk_user, random_name, profile_regions, region, is_success):
        with configure_regions(["r1", "r2"]):
            # Update user enabled regions
            user_profile = UserProfile.objects.get_profile(bk_user)
            user_profile.enable_regions = ";".join(profile_regions)
            user_profile.save()

            app_json = make_app_desc(random_name, region=region)
            controller = AppDeclarativeController(bk_user)
            if not is_success:
                with pytest.raises(DescriptionValidationError) as exc_info:
                    controller.perform_action(get_app_description(app_json))
                assert "region" in exc_info.value.detail
            else:
                controller.perform_action(get_app_description(app_json))

    def test_normal(self, bk_user, random_name):
        app_json = make_app_desc(random_name)
        app_json["bk_app_name"] = random_name
        controller = AppDeclarativeController(bk_user)
        controller.perform_action(get_app_description(app_json))

    def test_i18n(self, bk_user, random_name):
        app_json = make_app_desc(random_name, introduction="introduction", description="description")
        app_json["bk_app_name"] = random_name
        controller = AppDeclarativeController(bk_user)
        application = controller.perform_action(get_app_description(app_json))

        with override("zh-cn"):
            assert application.get_product().introduction == "introduction"
            assert application.get_product().description == "description"
        with override("en"):
            assert application.get_product().introduction == "noitcudortni"
            assert application.get_product().description == "noitpircsed"


class TestAppDeclarativeControllerUpdate:
    @pytest.fixture()
    def existed_app(self, bk_user, random_name):
        """Create an application before to test update"""
        app_json = make_app_desc(random_name)
        controller = AppDeclarativeController(bk_user)
        controller.perform_action(get_app_description(app_json))
        return Application.objects.get(code=random_name)

    def test_without_permission(self, bk_user, existed_app):
        another_user = create_user(username="another_user")
        app_json = make_app_desc(existed_app.code)

        controller = AppDeclarativeController(another_user)
        with pytest.raises(DescriptionValidationError) as exc_info:
            controller.perform_action(get_app_description(app_json))
        assert "bk_app_code" in exc_info.value.detail

    def test_region_modified(self, bk_user, existed_app):
        # Get a different and valid region
        regions = get_all_regions().keys()
        diff_region = [r for r in regions if r != existed_app.region][0]

        # Use new region
        app_json = make_app_desc(existed_app.code)
        app_json["bk_app_name"] = existed_app.name
        app_json["region"] = diff_region
        controller = AppDeclarativeController(bk_user)
        with pytest.raises(DescriptionValidationError) as exc_info:
            controller.perform_action(get_app_description(app_json))
        assert "region" in exc_info.value.detail

    def test_name_modified(self, bk_user, existed_app):
        # Use new name
        app_json = make_app_desc(existed_app.code)
        app_json["bk_app_name"] = existed_app.name + "2"

        controller = AppDeclarativeController(bk_user)
        with pytest.raises(DescriptionValidationError) as exc_info:
            controller.perform_action(get_app_description(app_json))
        assert "bk_app_name" in exc_info.value.detail

    def test_normal(self, bk_user, existed_app):
        app_json = make_app_desc(existed_app.code)
        app_json["bk_app_name"] = existed_app.name

        controller = AppDeclarativeController(bk_user)
        controller.perform_action(get_app_description(app_json))


class TestMarketField:
    def test_creation(self, bk_user, random_name, tag):
        app_desc = make_app_desc(random_name, tag=tag, introduction=random_name)
        controller = AppDeclarativeController(bk_user)
        controller.perform_action(get_app_description(app_desc))

        product = Product.objects.get(code=random_name)
        assert product.tag == tag
        assert product.introduction == random_name

    def test_update_partial(self, bk_user, random_name):
        app_desc = make_app_desc(random_name, introduction="foo", description="foo")
        AppDeclarativeController(bk_user).perform_action(get_app_description(app_desc))
        product = Product.objects.get(code=random_name)
        assert product.introduction == "foo"
        assert product.description == "foo"

        # Update with description omitted
        app_desc = make_app_desc(random_name, introduction="bar")
        AppDeclarativeController(bk_user).perform_action(get_app_description(app_desc))
        product = Product.objects.get(code=random_name)
        assert product.introduction == "bar"
        assert product.description == "foo"


class TestMarketDisplayOptionsField:
    def test_creation_omitted(self, bk_user, random_name, tag):
        minimal_app_desc = make_app_desc(random_name, display_options=None)
        controller = AppDeclarativeController(bk_user)
        controller.perform_action(get_app_description(minimal_app_desc))

        product = Product.objects.get(code=random_name)
        assert product.tag is None
        assert product.introduction == random_name
        assert product.displayoptions.width == 1280
        assert product.displayoptions.height == 600
        assert product.displayoptions.is_win_maximize is False
        assert product.displayoptions.visible is True
        assert product.displayoptions.open_mode == "new_tab"

    def test_update_partial(self, bk_user, random_name, tag):
        app_desc = make_app_desc(random_name, display_options={"width": 99, "height": 99, "open_mode": "desktop"})
        controller = AppDeclarativeController(bk_user)
        controller.perform_action(get_app_description(app_desc))

        app_desc = make_app_desc(random_name, display_options={"height": 10, "open_mode": "new_tab"})
        AppDeclarativeController(bk_user).perform_action(get_app_description(app_desc))

        product = Product.objects.get(code=random_name)
        # `width` field should not be affected
        assert product.displayoptions.width == 99
        assert product.displayoptions.height == 10
        assert product.displayoptions.open_mode == "new_tab"


class TestServicesField:
    @pytest.fixture(autouse=True, params=["legacy-local", "newly-local"])
    def _default_services(self, request):
        """Create local services in order by run unit tests"""
        category = G(ServiceCategory, id=Category.DATA_STORAGE)
        service_names = ["mysql", "rabbitmq"]
        for name in service_names:
            # Create service object
            svc = G(Service, name=name, category=category, region=settings.DEFAULT_REGION_NAME, logo_b64="dummy")
            # Create default plans
            if request.param == "legacy-local":
                G(Plan, name="no-ha", service=svc, config="{}", is_active=True)
                G(Plan, name="ha", service=svc, config="{}", is_active=True)
            else:
                G(Plan, name=generate_random_string(), service=svc, config="{}", is_active=True)

    @pytest.fixture()
    def app_desc(self, random_name, tag):
        return make_app_desc(
            random_name,
            introduction="应用简介",
            display_options={"open_mode": "desktop"},
            services=[{"name": "mysql"}],
        )

    def test_creation(self, bk_user, random_name, tag, app_desc):
        controller = AppDeclarativeController(bk_user)
        controller.perform_action(get_app_description(app_desc))

        service_obj = mixed_service_mgr.find_by_name("mysql", settings.DEFAULT_REGION_NAME)
        application = Application.objects.get(code=random_name)
        assert mixed_service_mgr.module_is_bound_with(service_obj, application.get_default_module()) is True

    def test_update_add(self, bk_user, random_name, tag, app_desc):
        controller = AppDeclarativeController(bk_user)
        controller.perform_action(get_app_description(app_desc))

        # Add a new service
        service_obj = mixed_service_mgr.find_by_name("rabbitmq", settings.DEFAULT_REGION_NAME)
        module = Application.objects.get(code=random_name).get_default_module()

        assert mixed_service_mgr.module_is_bound_with(service_obj, module) is False
        app_desc["modules"][random_name]["services"].append({"name": service_obj.name})
        controller.perform_action(get_app_description(app_desc))
        assert mixed_service_mgr.module_is_bound_with(service_obj, module) is True

    def test_not_existed_service(self, bk_user, random_name, tag, app_desc):
        app_desc["modules"][random_name]["services"] = [{"name": "invalid-service"}]

        controller = AppDeclarativeController(bk_user)
        controller.perform_action(get_app_description(app_desc))

        application = Application.objects.get(code=random_name)
        services = mixed_service_mgr.list_binded(application.get_default_module())
        assert len(list(services)) == 0

    def test_shared_service(self, bk_user, random_name, tag, app_desc):
        app_desc["modules"][random_name + "1"] = {
            "is_default": False,
            "language": "python",
            "services": [{"name": "mysql", "shared_from": random_name}],
        }
        controller = AppDeclarativeController(bk_user)
        controller.perform_action(get_app_description(app_desc))

        service_obj = mixed_service_mgr.find_by_name("mysql", settings.DEFAULT_REGION_NAME)
        application = Application.objects.get(code=random_name)
        module = application.get_module(random_name + "1")
        ref_module = application.get_module(random_name)
        info = ServiceSharingManager(module).get_shared_info(service_obj)
        assert info is not None
        assert info.ref_module == ref_module
        assert info.module == module

    def test_shared_service_but_module_not_found(self, bk_user, random_name, tag, app_desc):
        app_desc["modules"][random_name + "1"] = {
            "is_default": False,
            "services": [{"name": "mysql", "shared_from": random_name + "2"}],
        }
        with pytest.raises(DescriptionValidationError):
            get_app_description(app_desc)
