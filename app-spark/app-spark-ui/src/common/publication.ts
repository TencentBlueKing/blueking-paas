import type {
  PublicationDeploymentRequest,
  PublicationDevCenterLinks,
  PublicationResponse,
} from '../http/types';

/** 本期始终发布后端认定的最新版本，请求里绝不能带 version_id。 */
export const createLatestDeploymentRequest = (
  publication: PublicationResponse,
  appName?: string,
): PublicationDeploymentRequest => {
  const name = appName?.trim();
  return publication.app_code === null && name ? { app_name: name } : {};
};

/** 已有线上版本且工作区出现了不同的新检查点时，才需要开放「更新版本」。 */
export const hasNewPublicationVersion = (publication: PublicationResponse | null): boolean => (
  Boolean(
    publication?.online
    && publication.latest_version_id
    && publication.latest_version_id !== publication.online.version_id,
  )
);

/** 兼容线上旧字段，并统一给发布面板提供开发者中心链接。 */
export const getPublicationLinks = (
  publication: PublicationResponse | null,
): PublicationDevCenterLinks | null => (
  publication?.dev_center_links ?? publication?.bkpaas_links ?? null
);
