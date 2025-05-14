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

from typing import Dict, Union

from blue_krill.data_types.enum import FeatureFlag, FeatureFlagField

from paasng.bk_plugins.pluginscenter.models import PluginDefinition, PluginInstance


class PluginFeatureFlag(FeatureFlag):  # type: ignore
    RE_RELEASE_HISTORY_VERSION = FeatureFlagField(label="重新发布历史版本", default=True)
    API_GATEWAY = FeatureFlagField(label="云 API 管理", default=False)
    PROCESS_MANAGE = FeatureFlagField(label="进程管理", default=False)
    STRUCTURE_LOG = FeatureFlagField(label="日志管理导航", default=False)
    APP_SECRETS = FeatureFlagField(label="应用密钥管理", default=False)
    PLUGIN_DISTRIBUTER = FeatureFlagField(label="插件使用方", default=False)
    CANCEL_RELEASE = FeatureFlagField(label="终止发布版本", default=True)
    SHOW_ENTRANCES_ADDRESS = FeatureFlagField(label="显示访问入口地址", default=False)
    CONFIGURATION_MANAGE = FeatureFlagField(label="配置管理", default=True)
    STDOUT_LOG = FeatureFlagField(label="标准输出日志", default=True)
    ACCESS_LOG = FeatureFlagField(label="访问日志日志", default=True)
    MARKET_INFO = FeatureFlagField(label="市场信息", default=True)
    PUBLISHER_INFO = FeatureFlagField(label="发布者", default=False)
    LOWER_REPO_NAME = FeatureFlagField(label="代码仓库名称转为小写字母", default=False)
    VISIBLE_RANGE_MANAGE = FeatureFlagField(label="可见范围导航", default=False)


class FeatureFlagsManagerBase:
    def __init__(self, features):
        self.features = features

    def list_all_features(self) -> Dict[str, bool]:
        feature_flag = PluginFeatureFlag.get_default_flags()
        for feature in self.features:
            feature_flag[feature.name] = feature.value
        return feature_flag

    def has_feature(self, feature_name: Union[str, PluginFeatureFlag]) -> bool:
        return self.list_all_features().get(feature_name, False)


class PluginFeatureFlagsManager(FeatureFlagsManagerBase):
    def __init__(self, plugin: PluginInstance):
        super().__init__(plugin.pd.features)
        self.plugin = plugin


class PluginDefinitionFlagsManager(FeatureFlagsManagerBase):
    def __init__(self, pd: PluginDefinition) -> None:
        super().__init__(pd.features)
        self.pd = pd
