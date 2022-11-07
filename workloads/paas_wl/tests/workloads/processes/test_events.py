# -*- coding: utf-8 -*-
import copy
import logging
from typing import List

from paas_wl.release_controller.process.events import ProcessEventType, ProcEventsProducer, ProcInstEventType
from paas_wl.release_controller.process.models import PlainProcess

logger = logging.getLogger(__name__)


class TestProcessEvents:
    def test_process_added(self, process, instance):
        before: List[PlainProcess] = []
        after = [process]

        producer = ProcEventsProducer(before, after)
        events = list(producer.produce())

        assert len(events) == 2
        assert events[0].type == ProcessEventType.CREATED
        assert events[0].invoker.type == 'web'

        assert events[1].type == ProcInstEventType.CREATED
        assert events[1].invoker.name == instance.name

    def test_process_removed(self, process, instance):
        before = [process]
        after: List[PlainProcess] = []

        producer = ProcEventsProducer(before, after)
        events = list(producer.produce())

        assert len(events) == 2
        assert events[0].type == ProcessEventType.REMOVED
        assert events[0].invoker.type == 'web'

        assert events[1].type == ProcInstEventType.REMOVED
        assert events[1].invoker.name == instance.name

    def test_process_updated_replicas(self, process):
        before = [process]
        after = [copy.deepcopy(process)]
        after[0].replicas = process.replicas + 1

        producer = ProcEventsProducer(before, after)
        events = list(producer.produce())

        assert len(events) == 1
        assert events[0].type == ProcessEventType.UPDATED_REPLICAS

    def test_process_updated_command(self, process):
        before = [process]
        after = [copy.deepcopy(process)]
        after[0].command = "bar"

        producer = ProcEventsProducer(before, after)
        events = list(producer.produce())

        assert len(events) == 1
        assert events[0].type == ProcessEventType.UPDATED_COMMAND
        assert events[0].invoker.command == 'bar'

    def test_proc_updated_instances_added(self, process, instance):
        before = [process]
        after = [copy.deepcopy(process)]
        new_instance = copy.deepcopy(instance)
        new_instance.name = "instance-bar"
        after[0].instances.append(new_instance)

        producer = ProcEventsProducer(before, after)
        events = list(producer.produce())

        assert len(events) == 1
        assert events[0].type == ProcInstEventType.CREATED
        assert events[0].invoker.name == new_instance.name

    def test_proc_updated_instances_removed(self, process, instance):
        before = [process]
        after = [copy.deepcopy(process)]
        after[0].instances = []

        producer = ProcEventsProducer(before, after)
        events = list(producer.produce())

        assert len(events) == 1
        assert events[0].type == ProcInstEventType.REMOVED
        assert events[0].invoker.name == instance.name

    def test_proc_updated_instances_updated_restarted(self, process, instance):
        before = [process]
        after = [copy.deepcopy(process)]
        after[0].instances[0].restart_count = 1

        producer = ProcEventsProducer(before, after)
        events = list(producer.produce())

        assert len(events) == 1
        assert events[0].type == ProcInstEventType.UPDATED_RESTARTED
        assert events[0].invoker.name == instance.name

    def test_proc_updated_instances_updated_ready(self, process, instance):
        before = [process]
        after = [copy.deepcopy(process)]
        after[0].instances[0].ready = True

        producer = ProcEventsProducer(before, after)
        events = list(producer.produce())

        assert len(events) == 1
        assert events[0].type == ProcInstEventType.UPDATED_BECOME_READY
        assert events[0].invoker.name == instance.name

    def test_proc_updated_instances_updated_not_ready(self, process, instance):
        before = [process]
        after = [copy.deepcopy(process)]
        instance.ready = True

        producer = ProcEventsProducer(before, after)
        events = list(producer.produce())

        assert len(events) == 1
        assert events[0].type == ProcInstEventType.UPDATED_BECOME_NOT_READY
        assert events[0].invoker.name == instance.name
