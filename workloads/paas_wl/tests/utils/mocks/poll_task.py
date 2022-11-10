# -*- coding: utf-8 -*-
import time

from blue_krill.async_utils.poll_task import PollingMetadata, PollingResult, TaskPoller


class FakeTaskPoller(TaskPoller):
    """A task poller for testing"""

    def query(self) -> PollingResult:
        return PollingResult.doing()

    @classmethod
    def create(cls, params):
        """Shortcut method to create poller instance"""
        metadata = PollingMetadata(retries=0, query_started_at=time.time(), queried_count=0)
        return cls(params, metadata)
