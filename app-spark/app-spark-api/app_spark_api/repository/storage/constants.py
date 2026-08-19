from django.db import models
from django.utils.translation import gettext_lazy as _


class StorageBackend(models.TextChoices):
    HOST_TMP_PATH = "host_tmp_path", _("主机临时路径")
    BK_REPO = "bk_repo", _("蓝鲸制品库")
