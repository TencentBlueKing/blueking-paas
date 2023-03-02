"""Provide functions for the apiserver module.

- Functions should be as few as possible
- Do not return the models in workloads directly when a simple data class is sufficient

Other modules which have similar purpose:

- paasng.engine.deploy.engine_svc.EngineDeployClient
- paasng.engine.models.processes.ProcessManager

These modules will be refactored in the future.
"""
from typing import Any, Dict, NamedTuple, Optional, Union
from uuid import UUID

from django.db import transaction

from paas_wl.cluster.constants import ClusterFeatureFlag
from paas_wl.cluster.models import Cluster
from paas_wl.cluster.serializers import ClusterSLZ
from paas_wl.networking.egress.misc import get_cluster_egress_ips
from paas_wl.platform.applications.models.app import WLEngineApp
from paas_wl.platform.applications.models.managers.app_metadata import EngineAppMetadata, get_metadata, update_metadata
from paas_wl.workloads.processes.models import ProcessSpec
from paasng.platform.applications.models import ModuleEnvironment
from paasng.platform.modules.models import Module


class CreatedAppInfo(NamedTuple):
    uuid: UUID
    name: str


def create_app_ignore_duplicated(region: str, name: str, type_: str) -> CreatedAppInfo:
    """Create an engine app object, return directly if the object already exists"""
    try:
        obj = WLEngineApp.objects.get(region=region, name=name)
    except WLEngineApp.DoesNotExist:
        obj = WLEngineApp.objects.create(region=region, name=name, type=type_)
    return CreatedAppInfo(obj.uuid, obj.name)


def get_metadata_by_env(env: ModuleEnvironment) -> EngineAppMetadata:
    """Get an environment's metadata"""
    wl_app = WLEngineApp.objects.get(pk=env.engine_app_id)
    return get_metadata(wl_app)


def update_metadata_by_env(env: ModuleEnvironment, metadata_part: Dict[str, Union[str, bool]]):
    """Update an environment's metadata, works like python's dict.update()

    :param metadata_part: An dict object which will be merged into app's metadata
    """
    wl_app = WLEngineApp.objects.get(pk=env.engine_app_id)
    update_metadata(wl_app, **metadata_part)


def delete_wl_resources(env: ModuleEnvironment):
    """Delete all resources of the given environment in workloads module, this function
    should be called when user deletes an application/module/env.

    :param env: Environment object.
    """
    from paas_wl.resources.actions.delete import delete_app_resources

    wl_app = env.engine_app.to_wl_obj()
    delete_app_resources(wl_app)

    # Delete some related records manually. Because during API migration, those related data
    # was stored in another database and the `Foreignkey` mechanism can't handle this situation.
    # TODO: Remove below lines when data was fully migrated
    ProcessSpec.objects.filter(engine_app_id=wl_app.pk).delete()

    wl_app.delete()


def delete_module_related_res(module: 'Module'):
    """Delete module's related resources"""
    from paas_wl.platform.applications.models_utils import delete_module_related_res as delete_wl_module_related_res

    with transaction.atomic(using="default"), transaction.atomic(using="workloads"):
        delete_wl_module_related_res(module)
        # Delete related EngineApp db records
        for env in module.get_envs():
            env.get_engine_app().delete()


def get_cluster_egress_info(region, cluster_name):
    """Get cluster's egress info"""
    cluster = Cluster.objects.get(region=region, name=cluster_name)
    return get_cluster_egress_ips(cluster)


def get_wl_app_cluster_name(engine_app_name: str) -> Optional[str]:
    wl_engine_app = WLEngineApp.objects.get(name=engine_app_name)
    return wl_engine_app.latest_config.cluster


def bind_wl_app_cluster(engine_app_name: str, cluster_name: str):
    wl_engine_app = WLEngineApp.objects.get(name=engine_app_name)
    cluster = Cluster.objects.get(name=cluster_name)
    latest_config = wl_engine_app.latest_config
    latest_config.cluster = cluster.name
    latest_config.mount_log_to_host = cluster.has_feature_flag(ClusterFeatureFlag.ENABLE_MOUNT_LOG_TO_HOST)
    latest_config.save()


def list_region_clusters(region):
    """List region clusters"""
    return ClusterSLZ(Cluster.objects.filter(region=region), many=True).data


def create_cnative_app_model_resource(region: str, data: Dict[str, Any]) -> Dict:
    """Create a cloud-native AppModelResource object

    :param region: Application region
    :param data: Payload for create resource
    :raises: ValidationError when CreateAppModelResourceSerializer validation failed
    """
    from paas_wl.cnative.specs.models import AppModelResource, create_app_resource
    from paas_wl.cnative.specs.serializers import AppModelResourceSerializer, CreateAppModelResourceSerializer

    serializer = CreateAppModelResourceSerializer(data=data)
    serializer.is_valid(raise_exception=True)
    d = serializer.validated_data

    resource = create_app_resource(
        # Use Application code as default resource name
        name=d['code'],
        image=d['image'],
        command=d.get('command'),
        args=d.get('args'),
        target_port=d.get('target_port'),
    )
    model_resource = AppModelResource.objects.create_from_resource(
        region, d['application_id'], d['module_id'], resource
    )
    return AppModelResourceSerializer(model_resource).data


def upsert_app_monitor(
    engine_app_name: str,
    port: int,
    target_port: int,
):
    from paas_wl.monitoring.app_monitor.models import AppMetricsMonitor

    instance, _ = AppMetricsMonitor.objects.update_or_create(
        defaults={
            "port": port,
            "target_port": target_port,
            "is_enabled": True,
        },
        app=WLEngineApp.objects.get(name=engine_app_name),
    )
