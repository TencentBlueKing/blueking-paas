# -*- coding: utf-8 -*-
import pytest

from paas_wl.workloads.processes.watch import ParallelChainedGenerator

pytestmark = pytest.mark.django_db


class TestParallelChainedGenerators:
    def test_normal(self):
        def lazy_range():
            yield from range(5)

        gen = ParallelChainedGenerator([lazy_range(), lazy_range()])
        gen.start()
        results = list(gen.iter_results())
        assert len(results) == 10
