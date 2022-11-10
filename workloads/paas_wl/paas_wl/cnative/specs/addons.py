import logging
from typing import Dict, List

from paas_wl.platform.external.client import get_plat_client

logger = logging.getLogger(__name__)


def list_addons(app_code: str, module_name: str, env: str) -> List[Dict]:
    """获取指定环境的增强服务启用/实例分配信息"""
    return get_plat_client().list_addons(app_code, module_name, env)
