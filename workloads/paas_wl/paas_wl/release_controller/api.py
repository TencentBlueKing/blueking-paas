from typing import Optional
from uuid import UUID

from paas_wl.platform.applications.models.build import Build, BuildProcess
from paas_wl.release_controller.builder.exceptions import InterruptionNotAllowed
from paas_wl.release_controller.builder.executor import interrupt_build
from paasng.platform.applications.models import ModuleEnvironment


def interrupt_build_proc(bp_id: UUID) -> bool:
    """Interrupt a build process

    :return: Whether the build process was successfully interrupted.
    """
    bp = BuildProcess.objects.get(pk=bp_id)
    if not bp.check_interruption_allowed():
        raise InterruptionNotAllowed()
    return interrupt_build(bp)


def get_latest_build_id(env: ModuleEnvironment) -> Optional[UUID]:
    """Get UUID of the latest build in the given environment

    :return: `None` if no builds can be found
    """
    try:
        return Build.objects.filter(app=env.wl_engine_app).latest('created').pk
    except Build.DoesNotExist:
        return None
