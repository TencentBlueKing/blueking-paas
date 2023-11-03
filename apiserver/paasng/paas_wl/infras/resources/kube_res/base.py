# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except
in compliance with the License. You may obtain a copy of the License at

    http://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software distributed under
the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the specific language governing permissions and
limitations under the License.

We undertake not to change the open source license (MIT license) applicable
to the current version of the project delivered to anyone in the future.
"""
import datetime
import logging
import time
from abc import ABCMeta, abstractmethod
from collections import OrderedDict
from contextlib import contextmanager
from dataclasses import dataclass
from typing import (
    TYPE_CHECKING,
    Callable,
    ContextManager,
    Dict,
    Generic,
    Iterator,
    List,
    NamedTuple,
    Optional,
    Type,
    TypeVar,
)

from kubernetes.client.exceptions import ApiException
from kubernetes.dynamic import ResourceField, ResourceInstance

from paas_wl.bk_app.applications.models import WlApp
from paas_wl.infras.resources.base import kres
from paas_wl.infras.resources.base.exceptions import NotAppScopedResource, ResourceDeleteTimeout, ResourceMissing
from paas_wl.infras.resources.kube_res.exceptions import (
    APIServerVersionIncompatible,
    AppEntityDeserializeError,
    AppEntityNotFound,
)
from paas_wl.infras.resources.utils.basic import get_client_by_app, get_client_by_cluster_name

if TYPE_CHECKING:
    from paas_wl.infras.resources.generation.mapper import MapperPack

logger = logging.getLogger(__name__)


@dataclass
class AppEntity:
    """Entity type related with WlApp"""

    app: WlApp
    name: str

    # If a resource was generated from kubernetes objects, the object will be stored
    # in this attribute and the resource will become "Concrete"
    # This field is useful for updating existed resource.
    _kube_data = None  # type: Optional[ResourceInstance]

    class Meta:
        """Metainfo of current AppEntity type"""

        # Kubernetes resource type bound with current entity
        kres_class: Type[kres.BaseKresource] = kres.BaseKresource
        deserializer: Optional[Type['AppEntityDeserializer']] = None
        deserializers: List[Type['AppEntityDeserializer']] = []

        # Optional:
        # When "serializer" was defined, current AppEntity type becomes applicable, which means it's
        # instances can be written back to kubernetes cluster.
        serializer: Optional[Type['AppEntitySerializer']] = None
        serializers: List[Type['AppEntitySerializer']] = []

    def __init_subclass__(cls) -> None:
        """Check if subclasses have defined required attributes"""
        if not hasattr(cls, 'Meta'):
            raise TypeError(f'{cls.__name__} must define "Meta" field')

        # Merge user defined Meta with default values
        for attr, value in AppEntity.Meta.__dict__.items():
            if attr.startswith('_') or hasattr(cls.Meta, attr):
                continue
            setattr(cls.Meta, attr, value)

        if cls.Meta.deserializer == NotImplemented:
            raise TypeError(f'{cls.__name__} must define "deserializer" in it\'s Meta class.')

    @classmethod
    def is_applicable(cls) -> bool:
        """Check if current type is applicable, which means it's object can be applied to kubernetes
        cluster.
        """
        return bool(cls.Meta.serializer or cls.Meta.serializers)

    def is_concrete(self) -> bool:
        """If this resource was retrieved from kubernetes, return True"""
        return bool(self._kube_data)

    def get_resource_version(self) -> Optional[str]:
        """Get resource_version of current object, return None if object is not concrete"""
        if self._kube_data:
            return self._kube_data.metadata.resourceVersion
        return None


AET = TypeVar("AET", bound=AppEntity)


class GVKConfig(NamedTuple):
    """Group/Version/Kind config for current AppEntity type"""

    server_version: str
    kind: str
    available_apiversions: List[str]
    preferred_apiversion: str


class BaseTransformer(Generic[AET]):
    """Base class for Serializer and Deserializer

    :param entity_type: Target entity type for transformation
    :param gvk_config: kubernetes "Group/Version/Kind" config, useful for making different payload
        for different cluster versions
    """

    # Specify an 'api_version', this property will be read by get_apiversion() method
    api_version = ''

    @staticmethod
    def get_api_version_from_gvk(gvk_config: GVKConfig) -> str:
        """dynamic api_version detected from gvk_config"""
        return ''

    def __init__(self, entity_type: Type[AET], gvk_config: GVKConfig):
        self.entity_type = entity_type
        self.gvk_config = gvk_config
        if self.api_version and self.api_version not in self.gvk_config.available_apiversions:
            raise APIServerVersionIncompatible(
                'APIServer does not support requested api_version, kind: {}, api_version: {}, '
                'gvk_config: {}'.format(self.entity_type.Meta.kres_class.kind, self.api_version, self.gvk_config)
            )

    def get_apiversion(self) -> str:
        """Get the exact apiVersion current transformer works with, if not defined, use the "preferred" apiVersion."""
        api_version = self.api_version or self.get_api_version_from_gvk(self.gvk_config)
        return api_version or self.gvk_config.preferred_apiversion


class AppEntityDeserializer(BaseTransformer, Generic[AET], metaclass=ABCMeta):
    """Base class for deserializing kube resource"""

    @abstractmethod
    def deserialize(self, app: WlApp, kube_data: ResourceInstance) -> AET:
        """Generate a AppEntity object by given kube object"""
        raise NotImplementedError


class AppEntitySerializer(BaseTransformer, Generic[AET], metaclass=ABCMeta):
    """Base class for serializing AppEntities"""

    @abstractmethod
    def serialize(self, obj: AET, original_obj: Optional[ResourceInstance] = None, **kwargs) -> Dict:
        """Generate kubernetes data by given AppEntity"""
        raise NotImplementedError


T = TypeVar('T', bound=BaseTransformer)


class EntityTransformerPicker(Generic[T]):
    """
    A special type which holds multiple serializers/deserializers,
    dynamically detect the most suitable transformer type according to the Kubernetes version.

    objects are chosen in below priority:
    - defined "api_version" and it's value in the `gvk_config.available_apiversions`
    - does not define "api_version"
    - IGNORES: defined "api_version" and it's value does not occurred in "available_apiversions"
    """

    transformer_mappings: Dict[str, Type[T]]

    def __init__(self, children_types: List[Type[T]]):
        self.children_types = children_types

    def get_transformer(self, entity_type: Type['AppEntity'], gvk_config: GVKConfig) -> T:
        """Try finding the proper transformer"""
        for child_type in self._iter_transformer_type(gvk_config):
            try:
                return child_type(entity_type, gvk_config)
            except APIServerVersionIncompatible as e:
                logger.warning(f'{child_type} does not match current gvk_config, skip. error: {e}')
                continue

        raise APIServerVersionIncompatible(
            f"No results can be found for {type(self).__name__}, "
            f"api versions: {str(self.transformer_mappings.keys())}, "
            f"gvk_config: {gvk_config}"
        )

    def _build_transformer_mappings(self, gvk_config: GVKConfig) -> Dict[str, Type[T]]:
        transformer_mappings = OrderedDict()
        for type_ in self.children_types:
            if api_version := type_.api_version:
                transformer_mappings[api_version] = type_
            elif get_api_version_from_gvk := getattr(type_, "get_api_version_from_gvk"):
                transformer_mappings[get_api_version_from_gvk(gvk_config)] = type_
            else:
                transformer_mappings[""] = type_
        return transformer_mappings

    def _iter_transformer_type(self, gvk_config: GVKConfig) -> Iterator[Type[T]]:
        self.transformer_mappings = self._build_transformer_mappings(gvk_config)
        available_apiversions = set(gvk_config.available_apiversions)
        available_apiversions.add(gvk_config.preferred_apiversion)

        # 为什么定义的优先级优于 preferred_apiversion？
        # api version 仅仅是某种资源声明规范，其行为受限于具体实现，而具体实现版本不容易获取和适配。
        # 另外 api version 本身并不一定稳定，可能会有新的特性加入，因此不同 k8s 版本的相同 api version 规范不一定相容。
        # 因此在实现中，应该优先适配稳定的 api version 的规范，以减轻开发成本。

        for api_version, transformer in self.transformer_mappings.items():
            if api_version in available_apiversions:
                yield transformer

        # 没有声明 api version 的看做通用实现，尽可能完成目标
        default_transformer_type = self.transformer_mappings.get("")
        if default_transformer_type:
            yield default_transformer_type


class EntityDeserializerPicker(EntityTransformerPicker[AppEntityDeserializer]):
    pass


class EntitySerializerPicker(EntityTransformerPicker[AppEntitySerializer]):
    pass


@dataclass
class ResourceList(Generic[AET]):
    """List container for multiple AppKubeResources"""

    items: List[AET]
    metadata: ResourceField

    def get_resource_version(self) -> str:
        """Return `resourceVersion` of current resource"""
        return self.metadata.resourceVersion


@dataclass
class WatchEvent(Generic[AET]):
    type: str
    res_object: Optional[AET] = None
    # 错误信息, 只有 type = ERROR 时有该字段
    error_message: str = ""


class NamespaceScopedReader(Generic[AET]):
    """A reader for namespace-scoped resources."""

    entity_type: Type[AET]

    def retrieve_associated_wl_app(self, kube_data: ResourceInstance) -> WlApp:
        """Detect the corresponding wl_app for the given kube_data

        This method retrieves the corresponding WlApp object associated with the given kube_data.
        If no such WlApp object is found, a NotAppScopedResource exception is raised.

        :return: The WlApp object associated with the given kube_data.
        :raise: NotAppScopedResource If no WlApp object is found for the given kube_data.
        """
        raise NotImplementedError

    def list_by_ns(self, cluster_name: str, namespace: str, labels: Optional[Dict] = None) -> List[AET]:
        """List resources from a specified namespace while optionally filtering based on labels."""
        return self.list_by_ns_with_mdata(cluster_name, namespace, labels).items

    def list_by_ns_with_mdata(
        self, cluster_name: str, namespace: str, labels: Optional[Dict] = None
    ) -> ResourceList[AET]:
        """List resources from a specified namespace while optionally filtering based on labels."""
        labels = labels or {}
        deserializer = self._make_deserializer(cluster_name)
        with self.kres(cluster_name, api_version=deserializer.get_apiversion()) as kres_client:
            ret = kres_client.ops_label.list(namespace=namespace, labels=labels)

        items = []
        for kube_data in ret.items:
            try:
                wl_app = self.retrieve_associated_wl_app(kube_data)
            except NotAppScopedResource:
                continue
            item = deserializer.deserialize(wl_app, kube_data)
            # Set _kube_data
            item._kube_data = kube_data
            items.append(item)
        return ResourceList[AET](items=items, metadata=ret.metadata)

    def watch_by_ns(
        self,
        cluster_name: str,
        namespace: str,
        labels: Optional[Dict] = None,
        resource_version: Optional[int] = None,
        ignore_unknown_objs: bool = False,
        **kwargs,
    ) -> Iterator[WatchEvent[AET]]:
        """Watch resources change event for a specified namespace

        :param cluster_name: name of the k8s cluster to watch
        :param namespace: the namespace to watch
        :param labels: labels for filtering results.
        :param resource_version: if resource_version is not None, watch changes relative to the given resource_version.
        :param ignore_unknown_objs: whether skip watch event when deserialize can not handle the object.
        """
        labels = labels or {}
        # set "resource_version" when it's value is not None
        # because None value will trigger apiserver error
        if resource_version:
            kwargs["resource_version"] = resource_version

        deserializer = self._make_deserializer(cluster_name)
        with self.kres(cluster_name, api_version=deserializer.get_apiversion()) as kres_client:
            try:
                for raw_event in kres_client.ops_label.create_watch_stream(
                    namespace=namespace, labels=labels, **kwargs
                ):
                    # When client given a staled resource_version, the watch stream will return an ERROR event
                    if raw_event["type"] == 'ERROR':
                        raw_object = raw_event["raw_object"]
                        msg = raw_object.get("message", "Unknown")
                        yield WatchEvent(type='ERROR', error_message=msg)
                        return

                    kube_data = raw_event["object"]
                    try:
                        wl_app = self.retrieve_associated_wl_app(kube_data)
                    except NotAppScopedResource:
                        continue

                    event = WatchEvent[AET](type=raw_event["type"])
                    try:
                        event.res_object = deserializer.deserialize(wl_app, raw_event["object"])
                    except AppEntityDeserializeError as e:
                        if ignore_unknown_objs:
                            logger.warning("failed to deserialize k8s resource %s, skip.", e.res)
                            continue
                        yield WatchEvent(type='ERROR', error_message=e.msg)
                        return
                    event.res_object._kube_data = raw_event["object"]
                    yield event
            except ApiException as exc:
                if self._exc_is_expired_rv(exc):
                    yield WatchEvent(type='ERROR', error_message=exc.reason)
                    return
                else:
                    raise

    @staticmethod
    def _exc_is_expired_rv(exc: ApiException) -> bool:
        """Check if an exception is raised because of expired ResourceVersion"""
        # Consider all responses with 401 status code as "resourceVersion expired" type error, stricter
        # checking like `"too old resource version" in exc.reason` sounds cool but it may also introduces
        # other problems in further Kubernetes versions.
        #
        # ref: https://kubernetes.io/docs/reference/using-api/api-concepts/#410-gone-responses
        return exc.status == 410

    def _make_deserializer(self, cluster_name: str) -> AppEntityDeserializer[AET]:
        gvk_config = self._load_gvk_config(cluster_name)
        if self.entity_type.Meta.deserializer:
            return self.entity_type.Meta.deserializer(self.entity_type, gvk_config)

        picker = EntityDeserializerPicker(self.entity_type.Meta.deserializers)
        ret = picker.get_transformer(self.entity_type, gvk_config)
        logger.debug('Picked deserializer:%s from multi choices, gvk_config: %s', ret.__class__.__name__, gvk_config)
        return ret

    def _load_gvk_config(self, cluster_name: str) -> GVKConfig:
        """Load GVK config of current Kind"""
        with self.kres(cluster_name) as kres_client:
            return GVKConfig(
                server_version=kres_client.version['kubernetes']['gitVersion'],
                kind=kres_client.kind,
                preferred_apiversion=kres_client.get_preferred_version(),
                available_apiversions=kres_client.get_available_versions(),
            )

    def _kres(self, cluster_name: str, api_version: str = '') -> Iterator[kres.BaseKresource]:
        """Return kres object as a context manager which was initialized with kubernetes client, will close all
        connection automatically when exit to avoid connections leaking.
        """
        with get_client_by_cluster_name(cluster_name) as client:
            yield self.entity_type.Meta.kres_class(client, api_version=api_version)

    kres: Callable[..., ContextManager['kres.BaseKresource']] = contextmanager(_kres)


class AppEntityReader(Generic[AET]):
    """Read app related kube resource, produces `AppEntity` objects

    :param entity_type: Bind current reader with this type, it must be subtype of AppEntity
    """

    def __init__(self, entity_type: Type[AET]):
        self.entity_type = entity_type

    def get(self, app: WlApp, name: str) -> AET:
        """Get a resource by name

        :raises: AppEntityNotFound if not found
        """
        deserializer = self._make_deserializer(app)
        with self.kres(app, api_version=deserializer.get_apiversion()) as kres_client:
            try:
                kube_data = kres_client.get(name, namespace=self._get_namespace(app))
            except ResourceMissing as e:
                raise AppEntityNotFound(f'{name} not found') from e

        res = deserializer.deserialize(app, kube_data)
        # Set _kube_data
        res._kube_data = kube_data
        return res

    def list_by_app(self, app: WlApp, labels: Optional[Dict] = None) -> List[AET]:
        """List all app's resources"""
        return self.list_by_app_with_meta(app, labels=labels).items

    def list_by_app_with_meta(self, app: WlApp, labels: Optional[Dict] = None) -> ResourceList[AET]:
        """List all app's resources,  return results including metadata

        :param labels: labels for filtering results
        """
        labels = labels or {}
        deserializer = self._make_deserializer(app)
        with self.kres(app, api_version=deserializer.get_apiversion()) as kres_client:
            ret = kres_client.ops_label.list(namespace=self._get_namespace(app), labels=labels)

        items = []
        for kube_data in ret.items:
            item = deserializer.deserialize(app, kube_data)
            # Set _kube_data
            item._kube_data = kube_data
            items.append(item)
        return ResourceList[AET](items=items, metadata=ret.metadata)

    def watch_by_app(
        self, app: WlApp, labels: Optional[Dict] = None, ignore_unknown_objs: bool = False, **kwargs
    ) -> Iterator[WatchEvent[AET]]:
        """Get notified when resource changes

        :param labels: labels for filtering results
        :param ignore_unknown_objs: whether skip watch event when deserialize can not handle the object
        """
        labels = labels or {}
        # Remove "resource_version" param when it's value is None because None value will trigger apiserver error
        if 'resource_version' in kwargs and kwargs['resource_version'] is None:
            kwargs.pop('resource_version')
        # watch_by_app must use namespace of app
        if kwargs.get("namespace"):
            # Setting "namespace" is not allowed, this function use the namespace of "app"
            raise ValueError('"namespace" is not supported')

        deserializer = self._make_deserializer(app)
        with self.kres(app, api_version=deserializer.get_apiversion()) as kres_client:
            try:
                for raw_event in kres_client.ops_label.create_watch_stream(
                    namespace=self._get_namespace(app), labels=labels, **kwargs
                ):
                    # When client given a staled resource_version, the watch stream will return an ERROR event
                    if raw_event["type"] == 'ERROR':
                        raw_object = raw_event["raw_object"]
                        msg = raw_object.get("message", "Unknown")
                        yield WatchEvent(type='ERROR', error_message=msg)
                        return

                    event = WatchEvent[AET](type=raw_event["type"])
                    try:
                        event.res_object = deserializer.deserialize(app, raw_event["object"])
                    except AppEntityDeserializeError as e:
                        if ignore_unknown_objs:
                            logger.warning("failed to deserialize k8s resource %s, skip.", e.res)
                            continue
                        yield WatchEvent(type='ERROR', error_message=e.msg)
                        return
                    event.res_object._kube_data = raw_event["object"]
                    yield event
            except ApiException as exc:
                if self._exc_is_expired_rv(exc):
                    yield WatchEvent(type='ERROR', error_message=exc.reason)
                    return
                else:
                    raise

    @staticmethod
    def _exc_is_expired_rv(exc: ApiException) -> bool:
        """Check if an exception is raised because of expired ResourceVersion"""
        # Consider all responses with 401 status code as "resourceVersion expired" type error, stricter
        # checking like `"too old resource version" in exc.reason` sounds cool but it may also introduces
        # other problems in further Kubernetes versions.
        #
        # ref: https://kubernetes.io/docs/reference/using-api/api-concepts/#410-gone-responses
        return exc.status == 410

    def _make_deserializer(self, app: WlApp) -> AppEntityDeserializer[AET]:
        gvk_config = self._load_gvk_config(app)
        if self.entity_type.Meta.deserializer:
            return self.entity_type.Meta.deserializer(self.entity_type, gvk_config)

        picker = EntityDeserializerPicker(self.entity_type.Meta.deserializers)
        ret = picker.get_transformer(self.entity_type, gvk_config)
        logger.debug('Picked deserializer:%s from multi choices, gvk_config: %s', ret.__class__.__name__, gvk_config)
        return ret

    def _load_gvk_config(self, app: WlApp) -> GVKConfig:
        """Load GVK config of current Kind"""
        with self.kres(app) as kres_client:
            # TODO: Add cache to avoid too many api calls
            return GVKConfig(
                server_version=kres_client.version['kubernetes']['gitVersion'],
                kind=kres_client.kind,
                preferred_apiversion=kres_client.get_preferred_version(),
                available_apiversions=kres_client.get_available_versions(),
            )

    def _kres(self, app: WlApp, api_version: str = '') -> Iterator[kres.BaseKresource]:
        """Return kres object as a context manager which was initialized with kubernetes client, will close all
        connection automatically when exit to avoid connections leaking.
        """
        with get_client_by_app(app) as client:
            yield self.entity_type.Meta.kres_class(client, api_version=api_version)

    kres: Callable[..., ContextManager['kres.BaseKresource']] = contextmanager(_kres)

    def _get_namespace(self, app: WlApp) -> str:
        """Return the namespace the kres object will create/query in"""
        return app.namespace


class AppEntityManager(AppEntityReader, Generic[AET]):
    """Help managing app related kube resource, allows writing AppEntity objects to kubernetes"""

    def __init__(self, entity_type: Type[AET]):
        super().__init__(entity_type)
        if not self.entity_type.is_applicable():
            raise TypeError(f'{self.entity_type} is not applicable, use AppEntityReader instead.')

    def save(self, res: AET):
        """Save a app related kube resource to kubernetes"""
        self.guide_res_argument(res)
        if res.is_concrete():
            self.update(res)
        else:
            self.create(res)

    def create(self, res: AET, **kwargs) -> AET:
        """Create a new app related kube resource"""
        self.guide_res_argument(res)
        serializer = self._make_serializer(res.app)
        body = serializer.serialize(res, **kwargs)
        with self.kres(res.app, api_version=serializer.get_apiversion()) as kres_client:
            kube_data = kres_client.create(res.name, body, namespace=self._get_namespace(res.app))
        # Set _kube_data
        res._kube_data = kube_data
        return res

    def delete_by_name(self, app: WlApp, name: str, non_grace_period: bool = False) -> 'WaitDelete[AET]':
        """Delete a resource by its name"""
        serializer = self._make_serializer(app)
        with self.kres(app, serializer.get_apiversion()) as kres_client:
            kres_client.delete(name, namespace=self._get_namespace(app), non_grace_period=non_grace_period)
            return WaitDelete(self, app=app, name=name, namespace=self._get_namespace(app))

    def upsert(self, res: AET, update_method='replace') -> AET:
        """Create or Update a new app related kube resource"""
        namespace = self._get_namespace(res.app)
        try:
            existed = self.get(app=res.app, name=res.name)
            res._kube_data = existed._kube_data
        except AppEntityNotFound:
            logger.info(f"{res.Meta.kres_class.kind}<%s/%s> does not exist, will create one", namespace, res.name)
            self.save(res)
            return res

        self.update(res, update_method=update_method)
        return res

    # Concrete methods start

    def update(self, res: AET, update_method='replace', mapper_version: Optional['MapperPack'] = None, **kwargs):
        """Update a resource, if resource does not exists, raise an exception instead.

        :param res: res can be concrete or non-concreate object, if it's a non-concrete resource,
            the update_method must be "patch" or a ValueError will be raised
        :raises: AppEntityNotFound if not found, ValueError if update_method is invalid
        """
        self.guide_res_argument(res)
        if not kwargs.get("allow_not_concrete", res.is_concrete()) and update_method != 'patch':
            raise ValueError('Only patch method is allowed for non-concrete resource')

        serializer = self._make_serializer(res.app)
        body = serializer.serialize(res, original_obj=res._kube_data, mapper_version=mapper_version)
        with self.kres(res.app, api_version=serializer.get_apiversion()) as kres_client:
            try:
                return kres_client.replace_or_patch(
                    name=res.name,
                    body=body,
                    namespace=self._get_namespace(res.app),
                    update_method=update_method,
                    **kwargs,
                )
            except ResourceMissing as e:
                raise AppEntityNotFound(f'{res.name} not found') from e

    def delete(self, res: AET, non_grace_period: bool = False) -> 'WaitDelete[AET]':
        """Delete a resource, it does not check if this resource exists in kubernetes apiserver or not."""
        self.guide_res_argument(res, allow_concrete_only=True)
        serializer = self._make_serializer(res.app)
        with self.kres(res.app, api_version=serializer.get_apiversion()) as kres_client:
            kres_client.delete(res.name, namespace=self._get_namespace(res.app), non_grace_period=non_grace_period)
            return WaitDelete(self, app=res.app, name=res.name, namespace=self._get_namespace(res.app))

    # Concreate methods end

    def _make_serializer(self, app: WlApp) -> AppEntitySerializer[AET]:
        """Make a serializer object by given AppEntity object"""
        gvk_config = self._load_gvk_config(app)
        if self.entity_type.Meta.serializer:
            return self.entity_type.Meta.serializer(self.entity_type, gvk_config)

        picker = EntitySerializerPicker(self.entity_type.Meta.serializers)
        ret = picker.get_transformer(self.entity_type, gvk_config)
        logger.debug('Picked serializer:%s from multi choices, gvk_config: %s', ret.__class__.__name__, gvk_config)
        return ret

    def guide_res_argument(self, res: AET, allow_concrete_only=False):
        """Raise exception when resource is invalid"""
        if not isinstance(res, self.entity_type):
            raise TypeError(f'Only {self.entity_type.__name__} is supported')
        if allow_concrete_only and not res.is_concrete():
            raise TypeError(f'resource {res.name} is not concrete')


class WaitDelete(Generic[AET]):
    """A helper to wait resource actually be deleted from the k8s server"""

    _check_interval = 1

    def __init__(self, reader: AppEntityReader[AET], app: WlApp, name: str, namespace: str):
        self.reader = reader
        self.app = app
        self.name = name
        self.namespace = namespace

    def wait(self, max_wait_seconds: int = 60, raise_timeout: bool = False) -> bool:
        """Wait for the resource to actually be deleted from the server.

        :param max_wait_seconds: the max wait time.
        :param raise_timeout: whether to throw an exception when timeout.
        :return: whether actually be deleted, `true` for be deleted.
        """
        now = datetime.datetime.now()
        when_timeout = now + datetime.timedelta(seconds=max_wait_seconds)
        while now <= when_timeout:
            time.sleep(self._check_interval)
            now = datetime.datetime.now()
            try:
                self.reader.get(app=self.app, name=self.name)
            except AppEntityNotFound:
                return True
        if raise_timeout:
            raise ResourceDeleteTimeout(
                resource_type=self.reader.entity_type.__name__, namespace=self.namespace, name=self.name
            )
        return False


@dataclass
class Schedule:
    """A schedule restriction for a resource(App)"""

    cluster_name: str
    tolerations: List
    node_selector: Dict
