# -*- coding: utf-8 -*-
from unittest.mock import MagicMock
from uuid import uuid4

from paas_wl.platform.applications.middlewares import InstancesInPlaceMiddleware
from paas_wl.platform.applications.permissions import AppAction, SiteAction

APPLICATION_PERMS_MAP = {
    AppAction.VIEW_BASIC_INFO: True,
    AppAction.BASIC_DEVELOP: True,
    AppAction.MANAGE_ADDONS_SERVICES: True,
    AppAction.MANAGE_ENV_PROTECTION: True,
    AppAction.MANAGE_MEMBERS: True,
    AppAction.MANAGE_APP_MARKET: True,
    AppAction.EDIT_BASIC_INFO: True,
    AppAction.DELETE_APPLICATION: True,
    AppAction.MANAGE_CLOUD_API: True,
    AppAction.MANAGE_ACCESS_CONTROL: True,
}

SITE_PERMISSION_MAP = {SiteAction.VISIT_SITE: True}


class TestInstancesInPlaceMiddleware:
    def test_integrated(self, rf):
        """Try trigger the middleware with some data, then query an EngineApp object"""
        engine_app_id = uuid4()
        extra_payload = {
            'insts': [
                {
                    'type': 'application',
                    'value': {
                        'application': {
                            'id': uuid4(),
                            'type': 'default',
                            'region': 'default',
                            'code': 'foo-app',
                            'name': 'fooApp',
                        },
                        'module': {'id': uuid4(), 'name': 'default'},
                        'module_env': {
                            'id': 10,
                            'environment': 'stag',
                            'engine_app_id': engine_app_id,
                            "is_offlined": False,
                        },
                        'engine_app': {'id': engine_app_id, 'name': 'bkapp-foo-app-stag'},
                    },
                    'perms_map': APPLICATION_PERMS_MAP,
                },
                {'type': 'global_site', 'value': 'nobody', 'perms_map': SITE_PERMISSION_MAP},
            ]
        }

        # Trigger middleware
        request = rf.get('/')
        request.extra_payload = extra_payload
        middleware = InstancesInPlaceMiddleware(MagicMock())
        middleware(request)
        assert request.insts_in_place.applications[0].code == 'foo-app'

        # Try query EngineApp object
        engine_app = request.insts_in_place.query_engine_app('foo-app', 'default', 'stag')
        assert engine_app.name == 'bkapp-foo-app-stag'

        # Test permission objects
        application = request.insts_in_place.get_application_by_code('foo-app')
        perm_obj = request.perms_in_place.get_application_perms(application)
        assert perm_obj.check_allowed(AppAction.BASIC_DEVELOP) is True

        site_perms_obj = request.perms_in_place.site_perms
        assert site_perms_obj.check_allowed(SiteAction.VISIT_SITE) is True

    def test_application_only(self, rf):
        """Try trigger the middleware with some data, then query an EngineApp object"""
        extra_payload = {
            'insts': [
                {
                    'type': 'application',
                    'value': {
                        'application': {
                            'id': uuid4(),
                            'type': 'default',
                            'region': 'default',
                            'code': 'foo-app',
                            'name': 'fooApp',
                        },
                        'module': None,
                        'module_env': None,
                        'engine_app': None,
                    },
                    'perms_map': APPLICATION_PERMS_MAP,
                }
            ]
        }

        # Trigger middleware
        request = rf.get('/')
        request.extra_payload = extra_payload
        middleware = InstancesInPlaceMiddleware(MagicMock())
        middleware(request)
        assert request.insts_in_place.applications[0].code == 'foo-app'
