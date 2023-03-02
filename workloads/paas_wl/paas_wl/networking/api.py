from paas_wl.networking.ingress.exceptions import DefaultServiceNameRequired, EmptyAppIngressError
from paas_wl.networking.ingress.managers import AppDefaultIngresses
from paas_wl.workloads.processes.controllers import module_env_is_running
from paasng.platform.applications.models import ModuleEnvironment


def sync_proc_ingresses(env: ModuleEnvironment):
    """Sync ingresses configs of the given env"""
    if not module_env_is_running(env):
        return

    wl_app = env.engine_app.to_wl_obj()
    for mgr in AppDefaultIngresses(wl_app).list():
        try:
            mgr.sync()
        except (DefaultServiceNameRequired, EmptyAppIngressError):
            continue
