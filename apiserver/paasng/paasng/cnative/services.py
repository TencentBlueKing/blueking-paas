# -*- coding: utf-8 -*-
from typing import Dict, List, Optional

from rest_framework.exceptions import ValidationError

from paasng.engine.constants import AppEnvName, EngineAppType
from paasng.engine.controller.cluster import get_region_cluster_helper
from paasng.engine.controller.exceptions import BadResponse
from paasng.engine.controller.state import controller_client
from paasng.engine.models import EngineApp
from paasng.platform.applications.models import Application, ModuleEnvironment
from paasng.platform.modules.models import Module
from paasng.utils.configs import get_region_aware
from paasng.utils.error_codes import error_codes

# Model-Resource
default_engine_app_prefix = 'bkapp'
default_environments: List[str] = [AppEnvName.STAG.value, AppEnvName.PROD.value]


def initialize_simple(module: Module, data: Dict, cluster_name: Optional[str] = None) -> Dict:
    """Initialize a cloud-native application, return the initialized object

    :param module: Module object, a module can only be initialized once
    :param data: Simple parameters for initialization, such as "image" and "command".
    :param cluster_name: The name of cluster to deploy BkApp.
    :raises: ValidationError when workloads service responds with "VALIDATION_ERROR"
    :raises: BadResponseError when fail to request workloads service
    """
    application = module.application
    default_data = {
        'application_id': str(application.id),
        'module_id': str(module.id),
        'code': application.code,
    }
    data.update(default_data)

    if not cluster_name:
        cluster_name = get_default_cluster_name(module.region)

    try:
        model_res = controller_client.create_cnative_app_model_resource(application.region, data)
    except BadResponse as e:
        if e.get_error_code() == 'VALIDATION_ERROR':
            detail = e.json_response.get('fields_detail', e.get_error_message())
            raise ValidationError(detail=detail)
        raise

    create_engine_apps(application, module, environments=default_environments, cluster_name=cluster_name)
    return model_res


def create_engine_apps(
    application: Application,
    module: Module,
    environments: Optional[List[str]] = None,
    cluster_name: Optional[str] = None,
):
    """Create engine app instances for application"""
    environments = environments or default_environments
    for environment in environments:
        engine_app_name = f'{default_engine_app_prefix}-{application.code}-{environment}'
        # 先创建 EngineApp，再更新相关的配置（比如 cluster_name）
        engine_app = get_or_create_engine_app(application.owner, application.region, engine_app_name)
        controller_client.update_app_config(application.region, engine_app_name, {'cluster': cluster_name})
        ModuleEnvironment.objects.create(
            application=application, module=module, engine_app_id=engine_app["uuid"], environment=environment
        )


def get_or_create_engine_app(owner: str, region: str, engine_app_name: str) -> Dict:
    """get or create engine app from workload"""
    try:
        created = controller_client.app__create(
            region=region, app_name=engine_app_name, app_type=EngineAppType.CLOUD_NATIVE
        )
        # Create EngineApp and binding relationships
        EngineApp.objects.create(
            id=created["uuid"],
            name=engine_app_name,
            owner=owner,
            region=region,
        )
        return created
    except BadResponse as e:
        if e.error_code == 'APP_ALREADY_EXISTS':
            return controller_client.app__retrive_by_name(region=region, app_name=engine_app_name)
        raise


def get_default_cluster_name(region: str) -> str:
    """get default cluster name from settings, and valid if we have this cluster."""
    try:
        default_cluster_name = get_region_aware("CLOUD_NATIVE_APP_DEFAULT_CLUSTER", region)
    except Exception as e:
        raise error_codes.CANNOT_CREATE_APP.f("暂无可用集群, 请联系管理员") from e

    cluster_helper = get_region_cluster_helper(region)
    for cluster in cluster_helper.list_clusters():
        if cluster.name == default_cluster_name:
            break
    else:
        raise error_codes.CANNOT_CREATE_APP.f(f"集群 {default_cluster_name} 未就绪, 请联系管理员")
    return default_cluster_name
