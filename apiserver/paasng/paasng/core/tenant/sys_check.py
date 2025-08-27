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
from django.apps import apps
from django.core.checks import Error, Warning, register


@register()
def check_model_multi_tenancy_configured(app_configs, **kwargs) -> list[Error]:
    """This function validates that first-party models are properly configured for multi-tenancy.
    It checks the following cases:

    1. Models with `tenant_id` field - pass
    2. Models with skip marker("not multi-tenancy") in docstring - pass
    3. Models with TODO marker in docstring - [WARNING]
    4. Models without any markers or tenant_id field - [ERROR]

    :return: The error list, it's empty when every model configures properly.
    """
    errors = []
    for model in get_first_party_models():
        doc_string = model.__doc__ or ""
        # Skip the deprecated models first
        if "[deprecated]" in doc_string:
            continue

        # Check if `tenant_id` field is configured
        has_tenant_id = any(field.name == "tenant_id" for field in model._meta.get_fields())
        if has_tenant_id:
            continue
        # Check the skip marker
        skip_marker = "[multi-tenancy] This model is not tenant-aware."
        if skip_marker in doc_string:
            continue

        # Check the TODO marker, if it's found, produce a warning message to ask the
        # developers to fix the issue ASAP.
        todo_marker = "[multi-tenancy] TODO"
        if todo_marker in doc_string:
            errors.append(
                Warning(
                    f"The model {model._meta.label} has not done multi-tenancy setup.",
                    hint="Complete the TODO by adding a field or setting a marker.",
                )
            )

            continue

        # All checks missed, add an error to fail the system checking procedure.
        errors.append(
            Error(
                f"The model {model._meta.label} does not meet the multi-tenancy requirements.",
                hint=(
                    "Add tenant_id field or add marker '[multi-tenancy] This model is not tenant-aware.' "
                    "in the docstring to skip."
                ),
            )
        )
    return errors


def get_first_party_models():
    """Return all first party models."""
    for app_config in apps.get_app_configs():
        # Only check the first party apps, skip others
        if not app_config.module.__name__.startswith(("paasng.", "paas_wl.")):
            continue
        yield from app_config.get_models()
