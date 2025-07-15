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
from typing import Any, Dict, List

from jsonschema import validate as jsonschema_validate
from jsonschema.exceptions import ValidationError as SchemaValidationError

from .exceptions import ComponentNotFound, ComponentPropertiesInvalid


class ComponentManager:
    def __init__(self, components_dir: Path):
        """
        初始化组件管理器

        :param components_dir: 组件根目录路径
        """
        self.components_dir = components_dir

    def get_all_components(self) -> Dict[str, Dict[str, Dict]]:
        """获取所有组件信息的结构化数据"""
        components: Dict[str, Dict[str, Dict]] = {}
        for component_type in self._get_component_types():
            components[component_type] = {}
            for version in self._get_component_versions(component_type):
                components[component_type][version] = {
                    "schema": self._get_component_schema(component_type, version),
                    "documentation": self._get_component_documentation(component_type, version),
                }
        return components

    def _get_component_schema(self, component_type: str, version: str) -> Dict:
        """获取组件 schema"""
        schema_file = self._get_component_file(component_type, version, "schema.json")
        return json.loads(schema_file.read_text())

    def _get_component_documentation(self, component_type: str, version: str) -> str:
        """获取组件说明文档"""
        doc_file = self._get_component_file(component_type, version, "docs.md")
        return doc_file.read_text()

    def validate_properties(self, component_type: str, version: str, properties: Dict[str, Any] | None):
        """验证组件参数"""
        schema = self._get_component_schema(component_type, version)
        if properties is not None:
            try:
                jsonschema_validate(instance=properties, schema=schema)
            except SchemaValidationError as e:
                raise ComponentPropertiesInvalid(f"component {component_type}:{version} properties invalid") from e

    def _get_component_file(self, component_type: str, version: str, filename: str) -> Path:
        """获取组件文件路径并验证"""
        file_path = self.components_dir / component_type / version / filename
        if not file_path.exists():
            raise ComponentNotFound(f"Component file not found: {file_path}")
        return file_path

    def _get_component_types(self) -> List[str]:
        """获取所有可用的组件类型"""
        return [d.name for d in self.components_dir.iterdir() if d.is_dir()]

    def _get_component_versions(self, component_type: str) -> List[str]:
        """获取指定组件类型的所有版本"""
        type_dir = self.components_dir / component_type
        if not type_dir.exists():
            raise ComponentNotFound(f"Component type not found: {component_type}")
        return [d.name for d in type_dir.iterdir() if d.is_dir()]
