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
from contextlib import contextmanager
from typing import Dict, List, Type


class PluginsContainer:
    """Plugin container Type"""

    classes: Dict[str, Type] = {}


_plugins = PluginsContainer()


def register_plugin(plugin_cls: Type):
    """Register a new service plugin class"""
    _plugins.classes[plugin_cls.__name__] = plugin_cls


def get_default_plugins() -> List[Type]:
    """Return all default plugin types"""
    return list(_plugins.classes.values())


@contextmanager
def override_plugins(plugins: List[Type]):
    """An context manager to override service plugins"""
    _orig_classes = _plugins.classes

    # Clear and register given plugins
    _plugins.classes = {}
    for plugin_cls in plugins:
        register_plugin(plugin_cls)

    yield
    # Restore original plugins
    _plugins.classes = _orig_classes
