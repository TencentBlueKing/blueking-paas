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

from paasng.bk_plugins.pluginscenter.definitions import ElasticSearchParams
from paasng.bk_plugins.pluginscenter.models import PluginInstance
from paasng.utils import safe_jinja2
from paasng.utils.es_log.search import SmartSearch


class ElasticSearchFilter:
    def __init__(self, plugin: PluginInstance, search_params: ElasticSearchParams):
        self.plugin = plugin
        self.search_params = search_params

    def filter_by_plugin(self, search: SmartSearch) -> SmartSearch:
        """为搜索增加插件相关过滤条件"""
        context = {"plugin_id": self.plugin.id}
        term_fields = self.search_params.termTemplate.copy()
        for k, v in term_fields.items():
            term_fields[k] = safe_jinja2.Template(v).render(**context)
        if term_fields:
            # [term] query doesn't support multiple fields
            for k, v in term_fields.items():
                search = search.filter("term", **{k: v})
        return search

    def filter_by_builtin_filters(self, search: SmartSearch) -> SmartSearch:
        """根据 params 配置的 builtinFilters 添加过滤条件"""
        if not self.search_params.builtinFilters:
            return search
        for key, value in self.search_params.builtinFilters.items():
            if isinstance(value, str):
                search = search.filter("term", **{key: value})
            else:
                search = search.filter("terms", **{key: value})
        return search

    def filter_by_builtin_excludes(self, search: SmartSearch) -> SmartSearch:
        """根据 params 配置的 builtinExcludes 添加过滤条件"""
        if not self.search_params.builtinExcludes:
            return search
        for key, value in self.search_params.builtinExcludes.items():
            if isinstance(value, str):
                search = search.exclude("term", **{key: value})
            else:
                search = search.exclude("terms", **{key: value})
        return search
