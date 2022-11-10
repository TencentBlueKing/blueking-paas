"""Resource Definition of `DomainGroupMapping` kind"""
from typing import List, Literal, Optional

from pydantic import BaseModel, validator

from paas_wl.cnative.specs.apis import ObjectMetadata
from paas_wl.cnative.specs.constants import ApiVersion


class Domain(BaseModel):
    """Domain object"""

    name: Optional[str] = None
    host: str
    pathPrefixList: List[str]

    # When provided, HTTPS will be enabled
    tlsSecretName: Optional[str] = None


class DomainGroup(BaseModel):
    """A group of domains

    :param source_type: From which source the Domain was provided, see
        `DomainGroupSource`
    """

    sourceType: str
    domains: List[Domain]


class MappingRef(BaseModel):
    """Reference subject for mapping object, currently only supports BkApp

    :param name: Name of BkApp resource object, must in same namespace
    """

    name: str
    kind: Literal['BkApp'] = 'BkApp'
    apiVersion: str = ApiVersion.V1ALPHA1.value


class DomainGroupMappingSpec(BaseModel):
    """Spec of DomainGroupMapping resource"""

    ref: MappingRef
    data: List[DomainGroup]


class DomainGroupMapping(BaseModel):
    """DomainGroupMapping resource, map a group of domains to a BkApp"""

    metadata: ObjectMetadata
    spec: DomainGroupMappingSpec
    apiVersion: str = ApiVersion.V1ALPHA1.value
    kind: Literal['DomainGroupMapping'] = 'DomainGroupMapping'

    @validator('apiVersion')
    def validate_api_version(cls, v) -> str:
        """ApiVersion can not be used for "Literal" validation directly, so we define a
        custom validator instead.
        """
        if v != ApiVersion.V1ALPHA1:
            raise ValueError(f'{v} is not valid, use {ApiVersion.V1ALPHA1}')
        return v
