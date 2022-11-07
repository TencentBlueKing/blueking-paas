# -*- coding: utf-8 -*-
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from paas_wl.release_controller.constants import ImagePullPolicy


@dataclass
class Runtime:
    """运行相关"""

    image: str
    # 实际的镜像启动命令
    command: Optional[List[str]] = None
    args: Optional[List[str]] = None
    envs: Dict[str, str] = field(default_factory=dict)
    image_pull_policy: ImagePullPolicy = field(default=ImagePullPolicy.IF_NOT_PRESENT)
    image_pull_secrets: List[Dict[str, str]] = field(default_factory=list)
