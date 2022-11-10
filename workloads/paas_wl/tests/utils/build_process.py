# -*- coding: utf-8 -*-
from django.utils.crypto import get_random_string

from paas_wl.platform.applications.models.app import App
from paas_wl.platform.applications.models.build import BuildProcess
from paas_wl.platform.applications.models.misc import OutputStream


def random_fake_bp(app: App, source_tar_path=None, revision=None, branch=None, image=None, buildpacks=None):
    source_tar_path = source_tar_path or get_random_string(10)
    revision = revision or get_random_string(10)
    branch = branch or get_random_string(10)

    build_process = BuildProcess.objects.create(
        owner=app.owner,
        app=app,
        source_tar_path=source_tar_path,
        revision=revision,
        branch=branch,
        output_stream=OutputStream.objects.create(),
        # 允许 none 参数
        image=image,
        buildpacks=buildpacks,
    )
    return build_process
