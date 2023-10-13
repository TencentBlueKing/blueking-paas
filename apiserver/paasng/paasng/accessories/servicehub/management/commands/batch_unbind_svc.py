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
import csv
from dataclasses import dataclass
from typing import Dict, List

from django.conf import settings
from django.core.management.base import BaseCommand

from paasng.accessories.servicehub.exceptions import ServiceObjNotFound
from paasng.accessories.servicehub.manager import SvcAttachmentDoesNotExist, mixed_service_mgr
from paasng.platform.applications.models import Application
from paasng.platform.applications.protections import ProtectedRes, raise_if_protected
from paasng.platform.modules.manager import ModuleCleaner
from paasng.platform.modules.models import Module


@dataclass
class BaseAppInfo:
    app_code: str
    app_name: str
    module_name: str
    env: str


class Command(BaseCommand):
    help = 'Bulk Unbundling Addon Services'

    def add_arguments(self, parser):
        parser.add_argument('--source', type=str, dest="source")
        parser.add_argument(
            "--name",
            required=True,
            type=str,
            help=("specify a service name"),
        )
        parser.add_argument("--region", required=False, type=str, default=settings.DEFAULT_REGION_NAME)
        parser.add_argument('--dry_run', dest="dry_run", action='store_true')

    def handle_input_data(self, source: str) -> Dict[str, Dict[str, List[str]]]:
        """
        从一个 .csv 文件中读取数据，文件中每一行的格式为：app_code,app_name,module_name,env
        处理后的数据格式为：{"app_code": {"module_name": ["stag", "prod"]}}

        :param source: .csv 文件的路径
        :return: 一个包含处理后数据的字典
        """
        data: Dict[str, Dict[str, List[str]]] = {}
        with open(source, 'r', encoding='utf-8') as csvfile:
            csv_reader = csv.reader(csvfile)
            for row in csv_reader:
                app_code, _, module_name, env = row

                if app_code not in data:
                    data[app_code] = {}

                if module_name not in data[app_code]:
                    data[app_code][module_name] = []

                data[app_code][module_name].append(env)
        return data

    def unbind_service_by_module(self, module: Module, app_code: str, service_id: str):
        """解绑模块下所有环境的增强服务，包含被共享的模块"""
        try:
            module_attachment = mixed_service_mgr.get_module_rel(module_id=module.id, service_id=service_id)
        except SvcAttachmentDoesNotExist:
            self.stdout.write(
                self.style.ERROR(
                    f"APP(code:{app_code})-module({module.name}) has no binding to the service<{service_id}>."
                )
            )
            return

        cleaner = ModuleCleaner(module=module)
        try:
            cleaner.delete_services(service_id=service_id)
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(
                    f"APP(code:{app_code})-module({module.name}) cannot unbundle the service<{service_id}>: {e}"
                )
            )
            return

        module_attachment.delete()
        self.stdout.write(
            self.style.SUCCESS(
                f"APP(code:{app_code})-module({module.name}) unbundle the service<{service_id}> Successfully."
            )
        )
        return

    def unbind_service_by_env(self, module: Module, app_code: str, env: str, service_id: str):
        """解绑环境绑定的增强服务实例"""
        engine_app = module.get_envs(env).engine_app
        # 这里拿到的是 EngineAppAttachment
        relations = mixed_service_mgr.list_all_rels(engine_app=engine_app, service_id=service_id)
        for rel in relations:
            rel.delete()
            self.stdout.write(
                self.style.SUCCESS(
                    f"APP(code:{app_code})-module({module.name})-env({env}) unbundle the service<{service_id}>."
                )
            )
        return

    def handle(self, source: str, name: str, region: str, dry_run: bool, *args, **options):
        """
        批量解绑增强的绑定关系

        :param source: .csv 文件的路径
        :param name: 服务名称
        :param region: 区域
        :param dry_run: 是否为模拟运行
        """
        try:
            service = mixed_service_mgr.find_by_name(name, region, include_invisible=True)
        except ServiceObjNotFound:
            self.stdout.write(self.style.WARNING(f"Addon service(name:{name},region:{region}) does not exist, skip"))
            return

        to_del_data = self.handle_input_data(source)
        if dry_run:
            self.stdout.write(self.style.SUCCESS(f"DRY-RUN: {to_del_data}"))
            return

        for app_code, app_data in to_del_data.items():
            try:
                application = Application.objects.get(code=app_code)
            except Application.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"APP(code:{app_code}) does not exist"))
                continue

            # 开启了增强服务保护则不能解绑、删除，比如 S-Mart 应用
            raise_if_protected(application, ProtectedRes.SERVICES_MODIFICATIONS)

            for module_name, env_list in app_data.items():
                module = application.get_module(module_name)
                svc_provisioned_envs = mixed_service_mgr.get_provisioned_envs(service, module)

                # 模块下已分配的实例都需要解绑，则直接解绑模块
                if set(svc_provisioned_envs).issubset(set(env_list)):
                    self.unbind_service_by_module(module, app_code, service.uuid)
                else:
                    # 只解绑对应的环境
                    for env in env_list:
                        self.unbind_service_by_env(module, env, app_code, service.uuid)
        return
