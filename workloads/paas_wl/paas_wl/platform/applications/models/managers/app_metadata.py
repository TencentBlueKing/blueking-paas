# -*- coding: utf-8 -*-
import logging
from typing import TYPE_CHECKING, Optional

import cattr
from attrs import define

if TYPE_CHECKING:
    from paas_wl.platform.applications.models.app import EngineApp

logger = logging.getLogger(__name__)


@define
class EngineAppMetadata:
    """An engine app's metadata object, contains essential information"""

    paas_app_code: str = ''  # Owner application's code
    module_name: str = ''  # Owner module's name
    environment: str = ''  # Bound environment name
    bkpa_site_id: Optional[int] = None  # Site ID for "PaaS Analysis" service
    acl_is_enabled: bool = False  # Whether ACL module is enabled

    def get_paas_app_code(self) -> str:
        """Get "paas_app_code" property, raise `RuntimeError` if result is empty, which
        means the source data might be corrupted.
        """
        if not self.paas_app_code:
            raise RuntimeError('"paas_app_code" is empty')
        return self.paas_app_code


def get_metadata(engine_app: 'EngineApp') -> EngineAppMetadata:
    """Get metadata object"""
    # TODO: Use `make_json_field()` to get structured object from Model directly
    json_data = engine_app.latest_config.metadata or {}
    return cattr.structure(json_data, EngineAppMetadata)


def update_metadata(engine_app: 'EngineApp', **kwargs) -> None:
    """Update engine_app's metadata by key, only valid keys(see `EngineAppMetadata`) are allowed

    :param kwargs: New metadata values
    """
    latest_config = engine_app.latest_config
    obj = cattr.structure(latest_config.metadata or {}, EngineAppMetadata)

    for key, value in kwargs.items():
        # If given key is not a valid attribute of EngineAppMetadata type, raise error
        if not hasattr(obj, key):
            raise ValueError(f'{key} is invalid')
        setattr(obj, key, value)

    latest_config.metadata = cattr.unstructure(obj)
    latest_config.save(update_fields=['metadata'])
