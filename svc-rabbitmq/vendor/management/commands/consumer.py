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
import logging
import time
import typing

from amqpstorm import Connection, Message
from django.core.management.base import BaseCommand
from django.utils.timezone import now

if typing.TYPE_CHECKING:
    from django.core.management.base import CommandParser

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Consume messages from rabbitmq"

    def add_arguments(self, parser: 'CommandParser'):
        parser.add_argument("-H", "--host", help="rabbitmq hostname")
        parser.add_argument("-P", "--port", type=int, default=5672, help="rabbitmq port")
        parser.add_argument("-u", "--user", default="guest", help="rabbitmq username")
        parser.add_argument("-p", "--password", default="guest", help="rabbitmq password")
        parser.add_argument("-V", "--vhost", default="/", help="rabbitmq vhost")
        parser.add_argument("-n", "--count", type=int, default=0, help="rabbitmq password")
        parser.add_argument("-d", "--delay", type=float, default=0, help="consume delay")
        parser.add_argument("-q", "--queue", help="rabbitmq message queue")
        parser.add_argument("-N", "--prefetch", type=int, default=None, help="prefetch message count")
        parser.add_argument("--read-only", default=False, action="store_true", help="do not ack message")
        parser.add_argument("--passive", default=False, action="store_true", help="do not create queue")

    def consume(
        self,
        connection: 'Connection',
        count: 'int',
        queue: 'str',
        read_only: 'bool',
        passive: 'bool',
        delay: 'float',
        prefetch: 'typing.Optional[int]',
        **options,
    ):
        consumed = 0

        def on_message(message: Message):
            nonlocal consumed
            consumed += 1
            print(f"{consumed} message[{now()}]: {message.body}")

            if delay:
                time.sleep(delay)

            if read_only:
                message.reject(requeue=True)
            else:
                message.ack()
            if count != 0 and consumed >= count:
                raise KeyboardInterrupt

        with connection.channel() as channel:
            channel.queue.declare(queue, auto_delete=True, passive=passive)

            if prefetch is None:
                prefetch = count

            channel.basic.qos(prefetch)

            channel.basic.consume(on_message, no_ack=False)
            channel.start_consuming()

    def handle(self, host, port, user, password, vhost, *args, **options):
        with Connection(hostname=host, port=port, username=user, password=password, virtual_host=vhost) as connection:
            try:
                self.consume(connection, **options)
            except KeyboardInterrupt:
                print("> done")
