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
from typing import Any, Callable, Dict, List, Optional


class AppDescV2Builder:
    @staticmethod
    def make_app_desc(
        random_name: str,
        *applys: Callable,
    ) -> Dict[str, Any]:
        """Make description data for testing"""
        result: Dict[str, Any] = {
            "region": None,
            "bk_app_code": random_name,
            "bk_app_name": random_name,
        }
        for apply in applys:
            apply(result)
        return result

    @staticmethod
    def with_module(
        module_name: str,
        is_default: bool,
        language: str = "python",
        source_dir: Optional[str] = None,
        services: Optional[List] = None,
        env_variables: Optional[List] = None,
        processes: Optional[Dict] = None,
    ):
        def apply(app_desc: Dict):
            if "modules" not in app_desc:
                app_desc["modules"] = {}
            if module_name in app_desc["modules"]:
                raise ValueError(f"module already exists: name={module_name}")

            module_desc = {
                "is_default": is_default,
                "language": language,
            }
            if source_dir:
                module_desc["source_dir"] = source_dir
            if services:
                module_desc["services"] = services
            if env_variables:
                module_desc["env_variables"] = env_variables
            if processes:
                module_desc["processes"] = processes
            app_desc["modules"][module_name] = module_desc

        return apply


class AppDescV3Builder:
    @staticmethod
    def make_app_desc(
        random_name: str,
        *applys: Callable,
    ) -> Dict[str, Any]:
        """Make description data for testing"""
        result: Dict[str, Any] = {
            "bkAppCode": random_name,
            "bkAppName": random_name,
        }
        for apply in applys:
            apply(result)
        return result

    @staticmethod
    def with_module(module_name: str, is_default: bool, language: str = "python", module_spec: Optional[Dict] = None):
        def apply(app_desc: Dict):
            if "modules" not in app_desc:
                app_desc["modules"] = []
            for module_desc in app_desc["modules"]:
                if module_desc["name"] == module_name:
                    raise ValueError(f"module already exists: name={module_name}")
            app_desc["modules"].append(
                {"name": module_name, "isDefault": is_default, "language": language, "spec": module_spec or {}}
            )

        return apply
