import { ref, watch } from 'vue';
import type { Ref } from 'vue';
import { getGitRepository } from '@/http/api';
import { resolveApiUrl } from '@/http/fetch';

/**
 * 项目源码压缩包的下载地址，没有可下的东西时为空串。
 *
 * 地址一律以后端给的 `archive_url` 为准，前端不按项目 ID 自己拼：它同时回答了「下载地址是什
 * 么」和「现在能不能下载」（远端仓库还没建起来时为 null），也给后端留了把归档挪到别处（对象存
 * 储、CDN）的余地——那时它会是个带协议的绝对地址。
 *
 * 取不到不抛也不提示：下载源码是这个页面的附带功能，失败时把入口藏起来即可，不该拿一句报错盖住
 * 用户真正在做的事（对话）。
 */
export const useSourceArchive = (projectId: Ref<string>) => {
  const archiveUrl = ref('');
  // 切项目之后，上一个项目的响应可能才姗姗来迟，用它认出「这已经不是当前项目的答案」。
  let requestToken = 0;

  watch(projectId, async (id) => {
    requestToken += 1;
    const token = requestToken;
    // 先清掉：换项目的这一瞬间，旧地址指向的是别人的源码，宁可没有入口也不能给错的。
    archiveUrl.value = '';
    if (!id) return;

    try {
      const repo = await getGitRepository(id);
      if (token !== requestToken) return;
      // resolveApiUrl 正好分这两种情况：带协议的绝对地址原样用，站内路径才补上 origin 与站点
      // 前缀——与其他接口走的是同一套拼装。
      archiveUrl.value = repo.archive_url ? resolveApiUrl(repo.archive_url) : '';
    } catch (error) {
      console.error('[project] 源码下载地址获取失败', error);
    }
  }, { immediate: true });

  return { archiveUrl };
};
