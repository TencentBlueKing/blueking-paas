# -*- coding: utf-8 -*-
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
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Text, Tuple
from urllib.parse import urljoin

import requests
from django.conf import settings
from pydantic import BaseModel, Field


class BaseResult(BaseModel):
    count: int = 0


class EventGenre(BaseModel):
    uuid: Text = ""
    name: Text = ""
    source: Text = ""


class EventGenreResult(BaseResult):
    results: List[EventGenre] = []


class EventRecord(BaseModel):
    uuid: Text = ""
    labels: Dict[Text, Text] = {}
    message: Text = ""
    key: Text = ""
    is_active: bool = False
    genre: EventGenre = EventGenre()
    created: datetime = Field(0)
    updated: datetime = Field(0)
    start: datetime = Field(0)
    end: datetime = Field(0)


class EventRecordStatus(BaseModel):
    uuid: Text = ""
    executor: Text = ""
    status: Text = ""
    details: Optional[Dict[Text, Any]] = {}
    created: datetime = Field(0)
    updated: datetime = Field(0)


class EventRecordDetails(EventRecord):
    status: List[EventRecordStatus] = []


class EventRecordResult(BaseResult):
    results: List[EventRecord] = []


class EventRecordMetrics(BaseModel):
    metric: Dict[Text, Text] = {}
    values: List[Tuple[float, float]] = []


class EventRecordMetricsResult(BaseModel):
    name: Text = ""
    operator: Text = ""
    threshold: float = 0
    results: List[EventRecordMetrics] = []


class GroupedEventRecord(BaseModel):
    labels: Dict[Text, Text] = {}
    count: int = 0
    record_ids: List[Text] = []


class GroupedEventRecordResult(BaseResult):
    results: List[GroupedEventRecord] = []


@dataclass
class Client:
    base_url: Text = field(default=settings.PHALANX_URL)
    auth_method: Text = field(default="iBearer")
    auth_token: Text = field(default=settings.PHALANX_AUTH_TOKEN)
    session: requests.Session = field(default_factory=requests.Session)

    def _get_record_filters(
        self,
        filters: Optional[Dict[Text, Any]] = None,
        labels: Optional[Dict[Text, Text]] = None,
        genre: Optional[Dict[Text, Any]] = None,
    ) -> Dict[Text, Any]:
        results = {}

        if filters:
            results.update(filters)

        if labels:
            results.update({f"labels.{k}": v for k, v in labels.items()})

        if genre:
            results.update({f"genre.{k}": v for k, v in genre.items()})

        return results

    def request(self, method, path, data=None, params=None):
        response = self.session.request(
            method=method,
            url=urljoin(self.base_url, path),
            data=data or {},
            params=params or {},
            headers={"Authorization": f"{self.auth_method} {self.auth_token}"},
        )
        if response.status_code == 404:
            return None

        response.raise_for_status()
        return response.json()

    def get_event_records(
        self,
        limit=100,
        offset=0,
        ordering="-start",
        search="",
        filters: Optional[Dict[Text, Any]] = None,
        labels: Optional[Dict[Text, Text]] = None,
        genre: Optional[Dict[Text, Any]] = None,
    ) -> Optional[EventRecordResult]:

        result = self.request(
            "post",
            "api/v1/paas/records/",
            params={"search": search},
            data={
                "offset": offset,
                "limit": limit,
                "ordering": ordering,
                **self._get_record_filters(filters=filters, labels=labels, genre=genre),
            },
        )
        if result is None:
            return None
        return EventRecordResult(**result)

    def get_event_record_metrics(self, uuid, start: datetime, end: datetime, step: Text):
        result = self.request(
            "get",
            f"api/v1/paas/records/{uuid}/metrics/",
            params={"start": start.isoformat(), "end": end.isoformat(), "step": step},
        )
        if result is None:
            return None
        return EventRecordMetricsResult(**result)

    def get_event_record_details(
        self,
        uuid,
        filters: Optional[Dict[Text, Any]] = None,
        labels: Optional[Dict[Text, Text]] = None,
        genre: Optional[Dict[Text, Any]] = None,
    ) -> Optional[EventRecordDetails]:
        result = self.request(
            "get",
            f"api/v1/paas/records/{uuid}/details/",
            params=self._get_record_filters(filters=filters, labels=labels, genre=genre),
        )
        if result is None:
            return None
        return EventRecordDetails(**result)

    def get_event_genre(
        self,
        limit=100,
        offset=0,
        ordering="created",
        filters: Optional[Dict[Text, Any]] = None,
    ) -> Optional[EventGenreResult]:
        filters = filters or {}
        result = self.request(
            "get",
            "api/v1/paas/genres/",
            params={"offset": offset, "limit": limit, "ordering": ordering, **filters},
        )
        if result is None:
            return None

        return EventGenreResult(**result)

    def get_grouped_records(
        self,
        groups: List[Text],
        ordering="-start",
        filters: Optional[Dict[Text, Any]] = None,
        labels: Optional[Dict[Text, Text]] = None,
        genre: Optional[Dict[Text, Any]] = None,
    ) -> Optional[GroupedEventRecordResult]:
        result = self.request(
            "post",
            "api/v1/paas/grouped/records/",
            data={
                "group": groups,
                "ordering": ordering,
                **self._get_record_filters(filters=filters, labels=labels, genre=genre),
            },
        )
        if result is None:
            return None

        return GroupedEventRecordResult(**result)
