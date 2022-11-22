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
import random
import signal
import socket
import typing
from multiprocessing import Event, Process
from time import sleep

from django.conf import settings
from django.core.cache import cache
from django.utils.translation import ugettext_lazy as _
from django_q.brokers import get_broker
from django_q.cluster import Cluster as QCluster
from django_q.cluster import Sentinel as QSentinel
from django_q.cluster import scheduler
from django_q.conf import Conf
from django_q.management.commands import qcluster
from django_q.status import Stat

if typing.TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class Sentinel(QSentinel):
    def __init__(self, cluster_id, stop_event, start_event, broker=None, timeout=Conf.TIMEOUT, start=True):
        super().__init__(stop_event, start_event, broker, timeout, False)
        # docker 里 ppid 一定是 1,只会导致冲突,不如直接改写
        self.parent_pid = cluster_id
        self.name = "Sentinel-%d" % cluster_id
        self.leader = None
        if start:
            self.start()

    def schedule(self):
        if not Conf.SCHEDULER:
            return
        # 保证只有一个 scheduler
        leader = cache.get_or_set(settings.TASK_LEADER_KEY, self.name, settings.TASK_LEADER_TTL)
        if self.name == leader:
            logger.info("%s become leader", self.name)
            scheduler(self.broker)
        elif leader != self.leader:
            logger.info("worker leader changed to %s", leader)
            self.leader = leader

    def guard(self):
        logger.info(_('{} guarding cluster at {}').format(self.name, self.pid))
        self.start_event.set()
        Stat(self).save()
        logger.info(_('Q Cluster-{} running.').format(self.parent_pid))
        self.schedule()
        counter = 0
        cycle = Conf.GUARD_CYCLE  # guard loop sleep in seconds
        # Guard loop. Runs at least once
        while not self.stop_event.is_set() or not counter:
            # Check Workers
            for p in self.pool:
                with p.timer.get_lock():
                    # Are you alive?
                    if not p.is_alive() or p.timer.value == 0:
                        self.reincarnate(p)
                        continue
                    # Decrement timer if work is being done
                    if p.timer.value > 0:
                        p.timer.value -= cycle
            # Check Monitor
            if not self.monitor.is_alive():
                self.reincarnate(self.monitor)
            # Check Pusher
            if not self.pusher.is_alive():
                self.reincarnate(self.pusher)
            # Call scheduler once a minute (or so)
            counter += cycle
            if counter >= 30:
                counter = 0
                self.schedule()
            # Save current status
            Stat(self).save()
            sleep(cycle)
        self.stop()


class Cluster(QCluster):
    def __init__(self, broker=None):
        self.broker = broker or get_broker()
        self.sentinel = None
        self.stop_event = None
        self.start_event = None
        self.cluster_id = random.randint(1000, 10000000)
        self.host = socket.gethostname()
        self.timeout = Conf.TIMEOUT
        self.stop_event = Event()
        self.start_event = Event()
        self.sentinel = Process(
            target=Sentinel,
            args=(
                self.cluster_id,
                self.stop_event,
                self.start_event,
                self.broker,
                self.timeout,
            ),
        )

    @property
    def pid(self):
        return self.cluster_id

    def start(self):
        # Start Sentinel
        self.sentinel.start()
        while not self.start_event.is_set():
            sleep(0.1)
        return self.pid


class Command(qcluster.Command):
    help = "Starts task worker."

    def add_arguments(self, parser):
        parser.add_argument(
            '--run-once',
            action='store_true',
            dest='run_once',
            default=False,
            help='Run once and then stop.',
        )

    def handle(self, *args, **options):
        q = Cluster()
        q.start()

        signal.signal(signal.SIGTERM, q.sig_handler)
        signal.signal(signal.SIGINT, q.sig_handler)

        if options.get('run_once', False):
            q.stop()
