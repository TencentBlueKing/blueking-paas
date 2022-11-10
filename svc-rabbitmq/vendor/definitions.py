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
from datetime import datetime, timedelta
from typing import Optional

from .utils import BaseFancyModel


class StatsRate(BaseFancyModel):
    rate: float = 0.0


class ChannelMessageStats(BaseFancyModel):
    publish: int = 0
    confirm_details: Optional[StatsRate] = None
    publish_details: Optional[StatsRate] = None


class ChannelConnectionDetails(BaseFancyModel):
    name: str = ""
    peer_host: str = ""
    peer_port: str = ""


class Channel(BaseFancyModel):
    messages_unacknowledged: int = 0
    messages_uncommitted: int = 0
    messages_unconfirmed: int = 0
    name: str = ""
    node: str = ""
    number: int = 0
    prefetch_count: int = 0
    state: str = ""
    transactional: bool = False
    user: str = ""
    vhost: str = ""
    consumer_count: int = 0
    global_prefetch_count: int = 0
    idle_since: Optional[datetime] = None
    acks_uncommitted: int = 0
    confirm: bool = False
    message_stats: Optional[ChannelMessageStats] = None
    connection_details: Optional[ChannelConnectionDetails] = None

    def is_consumer(self):
        return self.consumer_count > 0

    def is_idle(self, ignore_consumer: bool = False, max_idle: Optional[timedelta] = None):
        if not ignore_consumer and self.consumer_count > 0:
            return False

        if not self.idle_since:
            return False

        if self.acks_uncommitted > 0:
            return False

        if self.messages_unacknowledged > 0:
            return False

        if self.messages_uncommitted > 0:
            return False

        if self.messages_unconfirmed > 0:
            return False

        if max_idle and self.idle_since + max_idle > datetime.utcnow():
            return False

        message_stats = self.message_stats
        if not message_stats:
            return True

        if message_stats.confirm_details and message_stats.confirm_details.rate > 0:
            return False

        if message_stats.publish_details and message_stats.publish_details.rate > 0:
            return False

        return True


class Connection(BaseFancyModel):
    auth_mechanism: str = ""
    channel_max: int = 0
    channels: int = 0
    connected_at: int = 0
    frame_max: int = 0
    host: str = ""
    name: str = ""
    node: str = ""
    peer_host: str = ""
    peer_port: int = 0
    port: int = 0
    protocol: str = ""
    recv_cnt: int = 0
    recv_oct: int = 0
    reductions: int = 0
    send_cnt: int = 0
    send_oct: int = 0
    send_pend: int = 0
    ssl: bool = False
    state: str = ""
    timeout: int = 0
    type: str = ""
    user: str = ""
    user_who_performed_action: str = ""
    vhost: str = ""
    recv_oct_details: Optional[StatsRate] = None
    send_oct_details: Optional[StatsRate] = None
    reductions_details: Optional[StatsRate] = None

    def is_busy(self):
        if self.recv_oct_details and self.recv_oct_details.rate > 0:
            return True

        if self.send_oct_details and self.send_oct_details.rate > 0:
            return True

    def __str__(self):
        return f"{self.vhost}({self.name})"
