import time
from typing import Callable, List, Optional

from paas_wl.bk_app.applications.models.release import Release
from paas_wl.bk_app.deploy.app_res.controllers import ProcessesHandler
from paas_wl.bk_app.processes.shim import ProcessManager
from paasng.platform.applications.models import ModuleEnvironment


def list_proc_types(env: ModuleEnvironment) -> List[str]:
    """List the process types for the given environment."""
    return [spec["name"] for spec in ProcessManager(env).list_processes_specs()]


def refresh_services(env: ModuleEnvironment):
    """Refresh the service resource for the given environment."""
    for proc_type in list_proc_types(env):
        # Recreate the service resource to select the new pods
        svc = ProcessesHandler.get_default_services(env.wl_app, proc_type)
        svc.remove()
        svc.create_or_patch()


def wait_for_release(
    release: Release, timeout_seconds: int = 120, interval_callback: Optional[Callable] = None
) -> bool:
    """Wait for the release to become ready.

    :param release: The release object.
    :param timeout_seconds: Max wait time in seconds.
    :param interval_callback: A callback function that will be called after each check.
    :return: bool, True if the release is ready, False otherwise.
    """
    st_time = time.time()
    while time.time() - st_time < timeout_seconds:
        if _release_is_ready(release):
            break
        if interval_callback:
            interval_callback()
        time.sleep(1)
    else:
        return False
    return True


def _release_is_ready(release: Release) -> bool:
    """Verify that a release is ready. It will ignore workloads that are not owned by the release,
    which is useful when there are resources owned by different mapper generations.
    """
    env = ModuleEnvironment.objects.get(engine_app_id=release.app_id)
    processes = ProcessManager(env).list_plain_processes()
    # Filter new process only, ignore processes using mapper v1
    matched_procs = [p for p in processes if p.version == release.version]
    if not matched_procs:
        return False
    return all(p.is_all_ready(release.version) for p in matched_procs)
