from dataclasses import dataclass, field
from typing import Dict, List, Optional

from paasng.engine.constants import ImagePullPolicy


@dataclass
class ContainerRuntimeSpec:
    """The runtime specification of a container which contains image, command and
    other info. Used for building Command and SlugBuilderTemplate.
    """

    image: str
    # The actual command for starting the container
    command: Optional[List[str]] = None
    args: Optional[List[str]] = None
    envs: Dict[str, str] = field(default_factory=dict)
    image_pull_policy: ImagePullPolicy = field(default=ImagePullPolicy.IF_NOT_PRESENT)
    image_pull_secrets: List[Dict[str, str]] = field(default_factory=list)
