# -*- coding: utf-8 -*-
from unittest.mock import MagicMock
from uuid import uuid4

from paas_wl.platform.applications.middlewares import InstancesInPlaceMiddleware

APPLICATION_PERMS_MAP = {
    'view_application': True,
    'checkout_source': True,
    'commit_source': True,
    'manage_services': True,
    'manage_processes': True,
    'view_logs': True,
    'manage_deploy': True,
    'manage_env_protection': True,
    'manage_members': True,
    'manage_product': True,
    'review_app': True,
    'edit_app': True,
    'delete_app': True,
    'manage_cloud_api': True,
    'manage_access_control': True,
}

SITE_PERMISSION_MAP = {'visit_site': True}


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
        assert perm_obj.check_allowed('manage_deploy') is True

        site_perms_obj = request.perms_in_place.site_perms
        assert site_perms_obj.check_allowed('visit_site') is True

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
