"""Resource Definition of `BkApplication` kind.

Use `pydantic` to get good JSON-Schema support, which is essential for CRD.
"""
import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, validator

from paas_wl.cnative.specs.apis import ObjectMetadata
from paas_wl.cnative.specs.constants import ApiVersion, MResPhaseType
from paas_wl.release_controller.constants import ImagePullPolicy

# Default resource limitations for each process
DEFAULT_PROC_CPU = '4000m'
DEFAULT_PROC_MEM = '1024Mi'


class MetaV1Condition(BaseModel):
    """Condition contains details for one aspect of the current state of this API Resource"""

    type: str
    status: Literal["True", "False", "Unknown"] = "Unknown"
    reason: str
    message: str
    observedGeneration: int = Field(default=0)


class BkAppProcess(BaseModel):
    """Process resource"""

    name: str
    image: str = Field(..., min_length=1)
    replicas: int = 1
    command: Optional[List[str]] = Field(default_factory=list)
    args: Optional[List[str]] = Field(default_factory=list)
    targetPort: Optional[int] = None
    cpu: str = DEFAULT_PROC_CPU
    memory: str = DEFAULT_PROC_MEM
    imagePullPolicy: str = ImagePullPolicy.IF_NOT_PRESENT


class Hook(BaseModel):
    """A hook object"""

    command: Optional[List[str]] = Field(default_factory=list)
    args: Optional[List[str]] = Field(default_factory=list)


class BkAppHooks(BaseModel):
    """Hook commands for BkApp"""

    preRelease: Optional[Hook] = None


class EnvVar(BaseModel):
    """Environment variable key-value pair"""

    name: str
    value: str


class BkAppConfiguration(BaseModel):
    """Configuration for BkApp"""

    env: List[EnvVar] = Field(default_factory=list)


class BkAppSpec(BaseModel):
    """Spec of BkApp resource"""

    processes: List[BkAppProcess] = Field(default_factory=list)
    hooks: Optional[BkAppHooks] = None
    configuration: BkAppConfiguration = Field(default_factory=BkAppConfiguration)


class BkAppStatus(BaseModel):
    """BkAppStatus defines the observed state of BkApp"""

    phase: str = MResPhaseType.AppPending
    observedGeneration: int = Field(default=0)
    conditions: List[MetaV1Condition] = Field(default_factory=list)
    lastUpdate: Optional[datetime.datetime]


class BkAppResource(BaseModel):
    """Blueking Application resource"""

    apiVersion: str = ApiVersion.V1ALPHA1.value
    metadata: ObjectMetadata
    spec: BkAppSpec
    kind: Literal['BkApp'] = 'BkApp'
    status: BkAppStatus = Field(default_factory=BkAppStatus)

    @validator('apiVersion')
    def validate_api_version(cls, v) -> str:
        """ApiVersion can not be used for "Literal" validation directly, so we define a
        custom validator instead.
        """
        if v != ApiVersion.V1ALPHA1:
            raise ValueError(f'{v} is not valid, use {ApiVersion.V1ALPHA1}')
        return v
