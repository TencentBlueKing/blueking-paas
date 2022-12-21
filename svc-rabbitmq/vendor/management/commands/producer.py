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
import logging
import time
import typing

from amqpstorm import Connection, Message
from django.core.management.base import BaseCommand
from django.template import Context, Template
from django.utils.timezone import now

if typing.TYPE_CHECKING:
    from amqpstorm import Channel
    from django.core.management.base import CommandParser

logger = logging.getLogger(__name__)


class PublishFailed(Exception):
    pass


class Command(BaseCommand):
    help = "Produce messages to rabbitmq"

    def add_arguments(self, parser: 'CommandParser'):
        parser.add_argument("-H", "--host", help="rabbitmq hostname")
        parser.add_argument("-P", "--port", type=int, default=5672, help="rabbitmq port")
        parser.add_argument("-u", "--user", default="guest", help="rabbitmq username")
        parser.add_argument("-p", "--password", default="guest", help="rabbitmq password")
        parser.add_argument("-V", "--vhost", default="/", help="rabbitmq vhost")
        parser.add_argument("-n", "--count", type=int, default=0, help="rabbitmq password")
        parser.add_argument(
            "-c", "--confirm", action="store_true", default=False, help="confirming message deliveries"
        )
        parser.add_argument("-d", "--delay", type=float, default=0, help="publish delay")
        parser.add_argument("-k", "--routing_key", help="rabbitmq message routing key")
        parser.add_argument("-e", "--exchange", default="", help="rabbitmq message exchange")
        parser.add_argument(
            "-t",
            "--template",
            default="{{ routing_key }} {% now 'H:i:s:u' %} {{ index }}/{{ count }}",
            help="rabbitmq message template, will rendered by django",
        )
        parser.add_argument("--passive", default=False, action="store_true", help="do not create queue")

    def publish(
        self,
        connection: 'Connection',
        count: 'int',
        routing_key: 'str',
        exchange: 'str',
        passive: 'bool',
        template: 'str',
        delay: 'float',
        confirm: 'bool',
        **options,
    ):
        with connection.channel() as channel:  # type: Channel
            channel.queue.declare(routing_key, auto_delete=True, passive=passive)

            if confirm:
                channel.confirm_deliveries()

            index = 1
            while True:
                if count != 0 and index > count:
                    break

                if not template:
                    template = input(f"message[{index}]: ")

                if not template:
                    continue

                body = Template(template).render(
                    Context(
                        {
                            "index": index,
                            "count": count,
                            "routing_key": routing_key,
                            "exchange": exchange,
                            "passive": passive,
                            **options,
                        }
                    )
                )

                message = Message.create(channel, body)
                confirmed = message.publish(
                    routing_key=routing_key, exchange=exchange, mandatory=True, immediate=False
                )
                if confirmed is False:
                    raise PublishFailed()

                print(f"{index} published[{now()}]: {body}")
                index += 1

                if delay:
                    time.sleep(delay)

    def handle(self, host, port, user, password, vhost, *args, **options):
        with Connection(hostname=host, port=port, username=user, password=password, virtual_host=vhost) as connection:
            try:
                self.publish(connection, **options)
            except KeyboardInterrupt:
                print("> done")
