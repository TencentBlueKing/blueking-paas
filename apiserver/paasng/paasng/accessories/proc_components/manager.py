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
from pathlib import Path
from typing import Any, Dict, List, Optional

from jsonschema import validate as jsonschema_validate
from jsonschema.exceptions import ValidationError as SchemaValidationError

from paasng.accessories.proc_components.constants import DEFAULT_COMPONENT_DIR

from .components import ComponentInfo
from .exceptions import ComponentNotFound, ComponentPropertiesInvalid


class ComponentLoader:
    def __init__(self):
        """初始化组件管理器"""
        self.components_dir = DEFAULT_COMPONENT_DIR

    def get_all_components(self) -> List[ComponentInfo]:
        """获取所有组件信息的列表数据"""
        components = []
        for component_name in self._get_component_names():
            for version in self._get_component_versions(component_name):
                components.append(
                    ComponentInfo(
                        name=component_name,
                        version=version,
                        schema=self.get_component_schema(component_name, version),
                        documentation=self._get_component_documentation(component_name, version),
                    )
                )
        return components

    def get_component_schema(self, component_name: str, version: str) -> Dict:
        """获取组件 schema"""
        schema_file = self._get_component_file(component_name, version, "schema.json")
        return json.loads(schema_file.read_text())

    def _get_component_documentation(self, component_name: str, version: str) -> str:
        """获取组件说明文档"""
        doc_file = self._get_component_file(component_name, version, "docs.md")
        return doc_file.read_text()

    def _get_component_file(self, component_name: str, version: str, filename: str) -> Path:
        """获取组件文件路径并验证"""
        file_path = self.components_dir / component_name / version / filename
        if not file_path.exists():
            raise ComponentNotFound(f"Component file not found: {file_path}")
        return file_path

    def _get_component_names(self) -> List[str]:
        """获取所有可用的组件类型"""
        return [d.name for d in self.components_dir.iterdir() if d.is_dir()]

    def _get_component_versions(self, component_name: str) -> List[str]:
        """获取指定组件类型的所有版本"""
        name_dir = self.components_dir / component_name
        if not name_dir.exists():
            raise ComponentNotFound(f"Component type not found: {component_name}")
        return [d.name for d in name_dir.iterdir() if d.is_dir()]


def validate_component_properties(component_name: str, version: str, properties: Optional[Any]):
    """验证组件参数"""
    loader = ComponentLoader()
    schema = loader.get_component_schema(component_name, version)
    if properties is not None:
        try:
            jsonschema_validate(instance=properties, schema=schema)
        except SchemaValidationError as e:
            raise ComponentPropertiesInvalid(f"component {component_name}:{version} properties invalid") from e
