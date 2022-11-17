"""
Tencent is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017-2022THL A29 Limited,
a Tencent company. All rights reserved.
Licensed under the MIT License (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the
specific language governing permissions and limitations under the License.

We undertake not to change the open source license (MIT license) applicable

to the current version of the project delivered to anyone in the future.
"""
import hashlib
from typing import Dict

from django.db.transaction import atomic
from django.shortcuts import get_object_or_404

from paasng.pluginscenter.exceptions import error_codes
from paasng.pluginscenter.models import PluginConfig, PluginDefinition, PluginInstance


class PluginConfigManager:
    def __init__(self, pd: PluginDefinition, plugin: PluginInstance):
        self.pd = pd
        self.plugin = plugin
        if pd.config_definition is None:
            raise ValueError("this plugin does not support configuration feature")

    @atomic
    def save(self, config_dict: Dict) -> PluginConfig:
        """Save a config dict as `PluginConfig` instance

        :param config_dict: Dict[column_key, column_value]
        :raise ValueError: when unique_key(config_dict) is conflict with an existed PluginConfig instance
        """
        unique_key = self.unique_key(config_dict)
        if "__id__" in config_dict:
            config_id = config_dict.pop("__id__")
            if unique_key == config_id:
                instance = get_object_or_404(PluginConfig, plugin=self.plugin, unique_key=config_id)
                instance.row = config_dict
                instance.save(update_fields=["row", "updated"])
                return instance
            # unique_key changed, delete old instance and create new one
            PluginConfig.objects.filter(plugin=self.plugin, unique_key=config_id).delete()

        if PluginConfig.objects.filter(plugin=self.plugin, unique_key=unique_key).exists():
            raise error_codes.CONFIGURATION_CONFLICT.f(conflict_fields=self.build_conflict_message(config_dict))
        return PluginConfig.objects.create(plugin=self.plugin, unique_key=unique_key, row=config_dict)

    def delete(self, unique_key: str):
        """Delete a PluginConfig

        :param unique_key: str
        """
        PluginConfig.objects.filter(plugin=self.plugin, unique_key=unique_key).delete()

    def unique_key(self, config_dict: Dict) -> str:
        """calculate an unique key for a config dict"""
        unique_columns = [column.name for column in self.pd.config_definition.columns if column.unique]
        values = [config_dict[column] for column in unique_columns]
        return hashlib.sha256(":".join(values).encode()).hexdigest()

    def build_conflict_message(self, config_dict: Dict) -> str:
        """build the unique key conflict message"""
        parts = [
            f"{column.title}={config_dict[column.name]}"
            for column in self.pd.config_definition.columns
            if column.unique
        ]
        return ",".join(parts)
