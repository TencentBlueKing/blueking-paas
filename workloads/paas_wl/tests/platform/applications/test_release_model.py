# -*- coding: utf-8 -*-
from django.test import TestCase

from tests.utils.app import random_fake_app, release_setup


class TestAppModel(TestCase):
    def setUp(self):
        self.app = random_fake_app()
        self.release = release_setup(fake_app=self.app)

    def test_release_failed(self):
        self.release.fail("hahahahaha")

        assert self.release.failed
        assert self.release.summary == "hahahahaha"
