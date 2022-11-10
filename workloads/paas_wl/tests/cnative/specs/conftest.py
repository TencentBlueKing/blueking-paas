from bkpaas_auth.models import User

from paas_wl.cnative.specs.constants import DeployStatus
from paas_wl.cnative.specs.models import AppModelDeploy, AppModelResource, create_app_resource
from paas_wl.platform.applications.struct_models import ModuleEnv


def create_cnative_deploy(env: ModuleEnv, user: User, status: DeployStatus = DeployStatus.READY) -> AppModelDeploy:
    """Initialize an app's model resource and create a deployment instance under
    given environment.

    :param env: The ModuleEnv object
    :param status: The status of deploy, "READY" by default
    """
    app = env.application
    module = env.module
    resource = create_app_resource(app.name, 'nginx:latest')
    model_res = AppModelResource.objects.create_from_resource(app.region, str(app.id), str(module.id), resource)
    return AppModelDeploy.objects.create(
        application_id=app.id,
        module_id=module.id,
        environment_name=env.environment,
        name='default-deploy-1',
        revision=model_res.revision,
        status=status.value,
        operator=user,
    )
