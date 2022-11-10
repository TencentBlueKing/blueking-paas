# -*- coding: utf-8 -*-
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
