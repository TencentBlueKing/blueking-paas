from uuid import UUID

from paas_wl.platform.applications.models.build import BuildProcess
from paas_wl.release_controller.builder.exceptions import InterruptionNotAllowed


def interrupt_build_proc(bp_id: UUID) -> bool:
    """Interrupt a build process

    :return: Whether the build process was successfully interrupted.
    """
    from paas_wl.release_controller.builder.executor import interrupt_build

    bp = BuildProcess.objects.get(pk=bp_id)
    if not bp.check_interruption_allowed():
        raise InterruptionNotAllowed()
    return interrupt_build(bp)
