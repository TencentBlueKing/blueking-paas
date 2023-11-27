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
from typing import Dict, List

from django.core.management.base import BaseCommand
from moby_distribution.registry.utils import parse_image

from paas_wl.infras.cluster.shim import get_application_cluster
from paasng.core.region.models import get_region
from paasng.platform.applications.models import Application
from paasng.platform.bkapp_model.models import ModuleProcessSpec
from paasng.platform.bkapp_model.utils import get_image_info
from paasng.platform.engine.constants import RuntimeType
from paasng.platform.engine.models.config_var import ConfigVar
from paasng.platform.modules.constants import SourceOrigin
from paasng.platform.modules.manager import initialize_module
from paasng.platform.modules.models.module import Module
from paasng.utils.validators import str2bool


class Command(BaseCommand):
    help = "migrate v1alpha1 multi images to v1alpha2 multi modules"

    def add_arguments(self, parser):
        parser.add_argument("--app-code", dest="app_code", required=True, help="应用code")
        parser.add_argument(
            "--clean-dirty-data",
            dest="clean_dirty_data",
            type=str2bool,
            help="清理 v1alpha1 dirty data",
            default=False,
        )

    def handle(self, app_code: str, clean_dirty_data: bool, *args, **options):
        """迁移策略: web 进程保留在 default 模块, 其他进程根据进程名单独创建模块"""
        default_module = Module.objects.get(application__code=app_code, name="default")

        if clean_dirty_data:
            ModuleProcessSpec.objects.filter(module=default_module).exclude(image__isnull=True).delete()
            return

        proc_specs = ModuleProcessSpec.objects.filter(module=default_module)
        images = {proc_spec.image for proc_spec in proc_specs if proc_spec.image is not None}
        image_repository, _ = get_image_info(default_module)

        if len(images) == 0 or image_repository:
            self.stdout.write(f"{app_code} has no multi images in default module, skip migration")
            return

        process_names = [proc_spec.name for proc_spec in proc_specs if proc_spec.name != "web"]
        if conflict_module_names := self._get_conflict_module_names(app_code, process_names):
            self.stdout.write(
                f"app_code({app_code}) process name ({', '.join(conflict_module_names)}) conflict with existed "
                f"module name, skip migration"
            )
            return

        application = Application.objects.get(code=app_code)
        cluster = get_application_cluster(application)
        proc_specs_maps = {proc_spec.name: proc_spec for proc_spec in proc_specs}
        for process_name in process_names:
            self._migrate_to_module(application, cluster.name, process_name, proc_specs_maps[process_name])

        ModuleProcessSpec.objects.filter(module=default_module, name="web").update(image=None)

        self.stdout.write(f"{app_code} migrate multi images success")

    def _get_conflict_module_names(self, app_code: str, new_module_names: List[str]) -> List[str]:
        return list(
            Module.objects.filter(application__code=app_code, name__in=new_module_names).values_list("name", flat=True)
        )

    def _migrate_to_module(
        self, application: Application, cluster_name: str, process_name: str, proc_spec: ModuleProcessSpec
    ):
        # 创建新模块
        module = Module.objects.create(
            application=application,
            is_default=False,
            region=application.region,
            name=process_name,
            owner=application.owner,
            creator=application.owner,
            exposed_url_type=get_region(application.region).entrance_config.exposed_url_type,
            source_origin=SourceOrigin(SourceOrigin.CNATIVE_IMAGE.value),
        )

        parsed = parse_image(proc_spec.image)
        image_repository = f"{parsed.domain}/{parsed.name}"

        bkapp_spec = {
            "build_config": {"build_method": RuntimeType.CUSTOM_IMAGE, "image_repository": image_repository},
            "processes": [self._build_process(process_name, proc_spec)],
        }

        # 初始化模块的各类配置
        initialize_module(
            module,
            repo_type="",
            repo_url=image_repository,
            repo_auth_info=None,
            cluster_name=cluster_name,
            bkapp_spec=bkapp_spec,
        )

        # 复制环境变量到新模块
        self._clone_config_vars(module)

    def _build_process(self, process_name: str, proc_spec: ModuleProcessSpec) -> Dict:
        env_overlay = {
            env_name: {
                "environment_name": env_name,
                "plan_name": proc_spec.get_plan_name(env_name),
                "target_replicas": proc_spec.get_target_replicas(env_name),
                "autoscaling": proc_spec.get_autoscaling(env_name),
                "scaling_config": proc_spec.get_scaling_config(env_name),
            }
            for env_name in ["stag", "prod"]
        }
        return {
            "name": process_name,
            "image_credential_name": proc_spec.image_credential_name,
            "command": proc_spec.command,
            "args": proc_spec.args,
            "port": proc_spec.port,
            "env_overlay": env_overlay,
        }

    def _clone_config_vars(self, module: Module):
        config_vars = [v.clone_to(module) for v in ConfigVar.objects.filter(module=module)]
        ConfigVar.objects.bulk_create(config_vars)
