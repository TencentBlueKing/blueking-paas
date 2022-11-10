from bkpaas_auth.core.constants import ProviderType
from bkpaas_auth.models import user_id_encoder


def username_to_id(username: str, provider_type: ProviderType) -> str:
    """Transform username to user id

    :param provider_type: user type, will be used for generating user id
    """
    return user_id_encoder.encode(provider_type, username)
