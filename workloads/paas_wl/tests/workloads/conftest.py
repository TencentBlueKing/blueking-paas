# -*- coding: utf-8 -*-
from bkpaas_auth.models import User

from paas_wl.platform.applications.models import EngineApp, Release
from paas_wl.platform.applications.struct_models import ModuleEnv


def create_release(env: ModuleEnv, user: User, failed: bool = False) -> Release:
    """Create a release in given environment.

    :return: The Release object
    """
    engine_app = EngineApp.objects.get_by_env(env)
    # Don't start from 1, because "version 1" will be ignored by `any_successful()`
    # method for backward-compatibility reasons
    version = Release.objects.count() + 10
    # Create the Release object manually without any Build object
    return Release.objects.create(
        owner=user.username,
        app=engine_app,
        failed=failed,
        config=engine_app.latest_config,
        version=version,
        summary='',
        procfile={},
    )
