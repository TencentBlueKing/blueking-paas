# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals

import urllib3
from django.test import TestCase

from paas_wl.release_controller.builder.utils import get_envs_for_pypi

urllib3.disable_warnings()


class TestBuilderUtils(TestCase):
    def test_get_envs_for_pypi(self):
        ret = get_envs_for_pypi('http://pypi.douban.com')
        assert ret['PIP_INDEX_URL'] == 'http://pypi.douban.com'
        assert ret['PIP_INDEX_HOST'] == 'pypi.douban.com'
