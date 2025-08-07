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

"""Collector for remote services"""

import logging
from collections import namedtuple
from typing import Dict, Generator, List, Optional

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from paasng.accessories.servicehub.remote.client import RemoteServiceClient, RemoteSvcConfig
from paasng.accessories.servicehub.remote.exceptions import FetchRemoteSvcError, RemoteClientError
from paasng.accessories.servicehub.remote.store import RemoteServiceStore
from paasng.utils.i18n.serializers import TranslatedCharField

logger = logging.getLogger(__name__)


class RemoteSvcFetcher:
    """Fetches remote services"""

    def __init__(self, config: RemoteSvcConfig):
        self.config = config
        self.client = RemoteServiceClient(config)

    def get_meta_info(self) -> Optional[Dict]:
        """Get service's metainfo"""
        try:
            data = self.client.get_meta_info()
        except RemoteClientError:
            return None

        if not MetaInfoSLZ(data=data).is_valid():
            return None
        return data

    def fetch(self):
        """Fetch services and plans from remote address"""
        try:
            json_data = self.client.list_services()
        except RemoteClientError as e:
            raise FetchRemoteSvcError("error fetching services.") from e

        items = self.validate_data(json_data)
        return items

    def validate_data(self, json_data) -> List[Dict]:
        """Validate json data

        :raises: FetchRemoteSvcError if data is invalid
        """
        items = []
        for svc_data in json_data:
            serializer = RemoteServiceSLZ(data=svc_data)
            try:
                serializer.is_valid(raise_exception=True)
            except ValidationError as e:
                logger.exception(f"service data from {self.config} validation failed")
                raise FetchRemoteSvcError(f"svc json data from {self.config} is invalid: {e}") from e
            items.append(serializer.validated_data)
        return items


# Serializers start


class MetaInfoSLZ(serializers.Serializer):
    version = serializers.CharField()


class RemotePlanSLZ(serializers.Serializer):
    uuid = serializers.CharField()
    name = serializers.CharField()
    properties = serializers.JSONField(default=dict)
    description = serializers.CharField()
    is_active = serializers.BooleanField(required=False, default=True)
    config = serializers.JSONField(required=False, default=dict)
    tenant_id = serializers.CharField(required=False)


class RemoteServiceSLZ(serializers.Serializer):
    uuid = serializers.CharField()

    category = serializers.IntegerField()
    name = serializers.CharField()
    display_name = TranslatedCharField()
    logo = serializers.CharField(allow_blank=True)
    description = TranslatedCharField(default="", allow_blank=True)
    long_description = TranslatedCharField(default="", allow_blank=True)
    instance_tutorial = TranslatedCharField(default="", allow_blank=True)
    available_languages = serializers.CharField()
    config = serializers.DictField(required=False, default=dict)
    is_active = serializers.BooleanField(required=False, default=True)
    is_visible = serializers.BooleanField()
    plans = RemotePlanSLZ(many=True)
    plan_schema = serializers.JSONField(required=False, default=dict)


# Serializers end


FetchResult = namedtuple("FetchResult", "config data meta_info")


def fetch_remote_service(config: RemoteSvcConfig) -> FetchResult:
    fetcher = RemoteSvcFetcher(config)
    meta_info = fetcher.get_meta_info()
    return FetchResult(config, fetcher.fetch(), meta_info)


def refresh_remote_service(remote_store: RemoteServiceStore, service_id: str):
    """Refresh the service"""
    remote_config = remote_store.get_source_config(service_id)
    ret = fetch_remote_service(config=remote_config)
    remote_store.bulk_upsert(ret.data, meta_info=ret.meta_info, source_config=ret.config)


def fetch_all_remote_services() -> Generator[FetchResult, None, None]:
    """Fetch all service data defined in config"""
    try:
        remote_svc_configs = settings.SERVICE_REMOTE_ENDPOINTS
    except AttributeError:
        raise ImproperlyConfigured("Can't initialize remote services, SERVICE_REMOTE_ENDPOINTS is not configured")
    if not isinstance(remote_svc_configs, list):
        raise ImproperlyConfigured("SERVICE_REMOTE_ENDPOINTS must be list type")

    for endpoint_conf in remote_svc_configs:
        config = RemoteSvcConfig.from_json(endpoint_conf)
        try:
            yield fetch_remote_service(config)
        except FetchRemoteSvcError:
            logger.exception("unable to load remote service.")
        except Exception:
            logger.exception("unable to load remote service.")
        else:
            logger.debug(f"successfully loaded {config}.")


def initialize_remote_services(remote_store: RemoteServiceStore):
    """Initialize remote services by settings"""
    for ret in fetch_all_remote_services():
        try:
            remote_store.bulk_upsert(ret.data, meta_info=ret.meta_info, source_config=ret.config)
        except Exception:
            logger.exception("update service failed.")
