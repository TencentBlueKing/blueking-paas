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

"""Command to upsert custom domain for application."""

import re

from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError

from paas_wl.workloads.networking.ingress.domains.independent import get_service_name
from paas_wl.workloads.networking.ingress.exceptions import ValidCertNotFound
from paas_wl.workloads.networking.ingress.managers import CustomDomainIngressMgr
from paas_wl.workloads.networking.ingress.models import Domain
from paas_wl.workloads.networking.ingress.signals import cnative_custom_domain_updated
from paasng.accessories.publish.market.constant import ProductSourceUrlType
from paasng.accessories.publish.market.models import MarketConfig
from paasng.platform.applications.constants import ApplicationType
from paasng.platform.applications.models import Application, Module

# Same regex as DomainEditableMixin.
DOMAIN_NAME_REGEX = re.compile(r"^[a-zA-Z0-9][-a-zA-Z0-9]{0,62}(\.[a-zA-Z0-9][-a-zA-Z0-9]{0,62})+\.?$")
PATH_PREFIX_REGEX = re.compile(r"^/([^/]+/?)*$")


class Command(BaseCommand):
    """Create or update a custom domain for an application.

    Example:
        python manage.py upsert_custom_domain --app_code bk_cmdb_saas --app_module web \
            --app_env prod --domain_name subpath-dev.example.com --path_prefix /cmdb/
    """

    help = "Create or update a custom domain for an application"

    def add_arguments(self, parser):
        parser.add_argument("--app_code", type=str, required=True, help="Application code")
        parser.add_argument("--app_module", type=str, required=True, help="Module name")
        parser.add_argument("--app_env", type=str, required=True, choices=["stag", "prod"], help="Environment name")
        parser.add_argument("--domain_name", type=str, required=True, help="Custom domain name (e.g., example.com)")
        parser.add_argument("--path_prefix", type=str, default="/", help="Path prefix (defaults to '/')")
        parser.add_argument("--https_enabled", action="store_true", help="Enable HTTPS for the domain")
        parser.add_argument(
            "--publish_app", action="store_true", help="Publish the app to the market after upserting the domain"
        )

    def handle(
        self, app_code, app_module, app_env, domain_name, path_prefix, https_enabled, publish_app, *args, **options
    ):
        # Get application, module, and environment
        try:
            application: Application = Application.objects.get(code=app_code)
            module = application.get_module(app_module)
        except Application.DoesNotExist:
            raise CommandError(f"Application '{app_code}' does not exist")
        except Module.DoesNotExist:
            raise CommandError(f"Module '{app_module}' does not exist in application '{app_code}'")

        env = module.envs.get(environment=app_env)
        # Validate domain data
        if not DOMAIN_NAME_REGEX.match(domain_name):
            raise CommandError(f"Validation failed: Domain name '{domain_name}' format is invalid")
        if not PATH_PREFIX_REGEX.match(path_prefix):
            raise CommandError(f"Validation failed: Path prefix '{path_prefix}' format is invalid")

        domain, _ = Domain.objects.update_or_create(
            tenant_id=application.tenant_id,
            name=domain_name,
            path_prefix=path_prefix,
            module_id=module.pk,
            environment_id=env.pk,
            defaults={"https_enabled": https_enabled},
        )

        # Sync domain config to Kubernetes
        # CNative: Processing is triggered by a signal (TLS not supported yet)
        # Normal: Directly sync Ingress resources (TLS certificates supported)
        if application.type == ApplicationType.CLOUD_NATIVE:
            try:
                cnative_custom_domain_updated.send(sender=env, env=env)
            except Exception as e:
                raise CommandError(f"Failed to deploy networking for cloud-native app: {e}")
        else:
            try:
                service_name = get_service_name(env.wl_app)
                CustomDomainIngressMgr(domain).sync(default_service_name=service_name)
            except ValidCertNotFound:
                raise CommandError("No valid certificate found for enabling HTTPS")
            except IntegrityError:
                raise CommandError(f"Domain '{domain_name}' is already in use")
            except Exception as e:
                raise CommandError(f"Failed to sync custom domain ingress: {e}")

        domain_url = f"{domain.protocol}://{domain.name}{path_prefix}"
        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully add custom domain:\n"
                f"  Domain URL: {domain_url}\n"
                f"  App Code: {app_code}\n"
                f"  Module: {app_module}\n"
                f"  Environment: {app_env}"
            )
        )

        if app_env == "prod" and publish_app:
            # Publish app to market
            market_config, _ = MarketConfig.objects.get_or_create_by_app(application)
            market_config.custom_domain_url = domain_url
            market_config.source_url_type = ProductSourceUrlType.CUSTOM_DOMAIN
            market_config.save()
            self.stdout.write(self.style.SUCCESS(f"App '{app_code}' published to market with URL: {domain_url}"))
