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

from django.core.management.base import BaseCommand

from paas_wl.workloads.networking.entrance.serializers import DomainSLZ, validate_domain_payload
from paas_wl.workloads.networking.ingress.domains.manager import get_custom_domain_mgr
from paasng.accessories.publish.market.constant import ProductSourceUrlType
from paasng.accessories.publish.market.models import MarketConfig
from paasng.platform.applications.models import Application


class Command(BaseCommand):
    help = "Add a custom address to the APP and publish it to the market."

    def add_arguments(self, parser):
        parser.add_argument(
            "--app_code",
            dest="app_code",
            required=True,
            type=str,
            help="APP ID",
        )
        parser.add_argument(
            "--domain",
            dest="app_domain",
            type=str,
            required=True,
            help="APP Domain",
        )
        parser.add_argument(
            "--module_name",
            dest="module_name",
            required=False,
            type=str,
            default="default",
            help="",
        )
        parser.add_argument(
            "--environment_name",
            dest="environment_name",
            required=False,
            type=str,
            default="prod",
            help="",
        )
        parser.add_argument(
            "--path_prefix",
            dest="path_prefix",
            default="/",
            type=str,
            required=False,
            help="APP access address path prefix",
        )
        parser.add_argument(
            "--scheme",
            dest="scheme",
            default="http",
            type=str,
            required=False,
            help="The protocol of the APP market address, default is HTTP.",
        )
        parser.add_argument(
            "--force",
            dest="force",
            default=False,
            type=bool,
            required=False,
            help="The protocol of the APP market address, default is HTTP.",
        )

    def handle(
        self, app_code, app_domain, module_name, environment_name, path_prefix, scheme, force, *args, **options
    ):
        application = Application.objects.get(code=app_code)
        if not force:
            # 校验应用访问地址合法性
            validate_domain_payload(
                {
                    "domain_name": app_domain,
                    "path_prefix": path_prefix,
                    "module_name": module_name,
                    "environment_name": environment_name,
                },
                application,
                serializer_cls=DomainSLZ,
            )

        env = application.get_module(module_name).get_envs(environment_name)
        # 开启 HTTPS 需要在集群内配置证书，暂时不对用户暴露这个参数
        get_custom_domain_mgr(application).create(
            env=env, host=app_domain, path_prefix=path_prefix, https_enabled=False
        )

        # 将应用的地址发布到市场
        market_url = f"{scheme}://{app_domain}{path_prefix}"
        market_config, _ = MarketConfig.objects.get_or_create_by_app(application)
        market_config.custom_domain_url = market_url
        market_config.source_url_type = ProductSourceUrlType.CUSTOM_DOMAIN
        market_config.save()
        self.stdout.write(
            self.style.SUCCESS(
                f"Add custom address({market_url}) to APP({app_code}), and successfully published it to the market."
            )
        )
