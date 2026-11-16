<template>
  <bk-popover
    ref="popoverRef"
    trigger="click"
    placement="bottom-end"
    theme="light"
    :arrow="false"
    :padding="0"
    ext-cls="publish-demo-popover"
    @after-show="handlePopoverShow"
    @after-hidden="handlePopoverHidden"
  >
    <button
      type="button"
      class="publish-trigger"
      :class="{
        'is-busy': Boolean(publication?.task),
        'is-online': Boolean(publication?.online) && !publication?.task,
        'has-failure': Boolean(publication?.last_failure) && !publication?.task,
        'is-open': visible,
      }"
    >
      <span v-if="publication?.task" class="publish-panel__spinner is-small" aria-hidden="true" />
      <span v-else-if="publication?.online" class="publish-trigger__dot" aria-hidden="true" />
      <AppIcon v-else name="globe" />
      <span>{{ triggerLabel }}</span>
    </button>

    <template #content>
      <section class="publish-panel" aria-label="发布项目">
        <template v-if="view === 'loading'">
          <header class="publish-panel__head"><h3>发布项目</h3></header>
          <div class="publish-panel__status">
            <span class="publish-panel__spinner" aria-hidden="true" />
            <p>正在获取发布状态…</p>
          </div>
        </template>

        <template v-else-if="view === 'load-error'">
          <header class="publish-panel__head"><h3>发布项目</h3></header>
          <div class="publish-panel__status is-error">
            <span class="publish-panel__status-mark"><AppIcon name="x" /></span>
            <h4>发布状态获取失败</h4>
            <p>{{ loadError }}</p>
          </div>
          <button
            type="button"
            class="publish-panel__primary"
            :disabled="refreshing"
            @click="pull()"
          >
            {{ refreshing ? '正在重试…' : '重试' }}
          </button>
        </template>

        <template v-else-if="publication">
          <header class="publish-panel__head">
            <button
              v-if="view === 'failure-detail'"
              type="button"
              class="publish-panel__back"
              aria-label="返回"
              @click="manualPage = null"
            >
              <AppIcon name="chevron-left" />
            </button>
            <h3>发布项目</h3>
            <span
              v-bk-tooltips="{ content: PUBLISH_HELP, placement: 'bottom-end' }"
              class="publish-panel__help"
            >
              <AppIcon name="help" />
            </span>
          </header>

          <template v-if="view === 'form'">
            <p class="publish-panel__desc">发布以获取可分享的公开访问地址。</p>
            <FailureBar
              v-if="publication.last_failure"
              :failure="publication.last_failure"
              @view="manualPage = 'failure'"
            />
            <PublicationAppNameField
              v-if="isFirstPublication"
              :model-value="appName"
              :pending="appNamePending"
              :result="appNameResult"
              @update:model-value="handleAppNameInput"
            />
            <div class="publish-panel__field">
              <span class="publish-panel__field-label">版本</span>
              <div
                v-if="publication.latest_version_id"
                v-bk-tooltips="'暂不支持选择版本'"
                class="publish-panel__version"
                aria-label="版本：当前工作区最新"
              >
                <span>当前工作区最新</span>
                <AppIcon name="chevron-down" />
              </div>
              <p v-else class="publish-panel__empty">
                暂无可用版本，先在左侧对话里开发一些功能吧。
              </p>
            </div>
            <p v-if="actionError" class="publish-panel__error" role="alert">{{ actionError }}</p>
            <button
              type="button"
              class="publish-panel__primary"
              :disabled="!canSubmit"
              @click="submitDeployment"
            >
              {{ submitting ? '正在提交…' : '发布' }}
            </button>
          </template>

          <template v-else-if="view === 'publishing'">
            <div class="publish-panel__status" role="status">
              <span class="publish-panel__spinner" aria-hidden="true" />
              <h4>{{ publication.task?.is_update ? '新版本发布中' : '发布进行中' }}</h4>
              <p>{{ progressText }}</p>
              <a
                v-if="publicationLinks?.deployments"
                class="publish-panel__link"
                :href="publicationLinks.deployments"
                target="_blank"
                rel="noopener noreferrer"
              >
                查看进度（跳转开发者中心）
                <AppIcon name="external-link" />
              </a>
            </div>
          </template>

          <template v-else-if="view === 'success'">
            <div class="publish-panel__banner">
              <span><AppIcon name="check" /></span>
              <div>
                <strong>项目已成功发布</strong>
                <p>把下面的地址分享给其他人即可访问</p>
              </div>
            </div>
            <OnlineDetails
              v-if="publication.online"
              :online="publication.online"
              :copied="copyDone"
              @copy="copyOnlineUrl"
            />
            <ManagedLinks :links="publicationLinks" />
          </template>

          <template v-else-if="view === 'online'">
            <FailureBar
              v-if="publication.last_failure"
              :failure="publication.last_failure"
              @view="manualPage = 'failure'"
            />
            <OnlineDetails
              v-if="publication.online"
              :online="publication.online"
              :copied="copyDone"
              @copy="copyOnlineUrl"
            />
            <ManagedLinks :links="publicationLinks" />
            <p v-if="actionError" class="publish-panel__error" role="alert">{{ actionError }}</p>
            <span
              v-bk-tooltips="{
                content: '线上已是当前工作区最新版本',
                disabled: hasNewVersion,
              }"
              class="publish-panel__button-wrap"
            >
              <button
                type="button"
                class="publish-panel__secondary"
                :disabled="!hasNewVersion || submitting"
                @click="submitDeployment"
              >
                {{ submitting ? '正在提交…' : '更新版本' }}
              </button>
            </span>
          </template>

          <template v-else>
            <div class="publish-panel__status is-error" role="alert">
              <span class="publish-panel__status-mark"><AppIcon name="x" /></span>
              <h4>{{ publication.last_failure?.is_update ? '更新版本失败' : '发布失败' }}</h4>
              <p
                v-if="publication.last_failure?.is_update && publication.online"
                class="publish-panel__status-note"
              >
                线上旧版本仍可正常访问
              </p>
              <p class="publish-panel__failure-message">{{ publication.last_failure?.error }}</p>
              <a
                v-if="publication.last_failure?.detail_url"
                class="publish-panel__link"
                :href="publication.last_failure.detail_url"
                target="_blank"
                rel="noopener noreferrer"
              >
                查看详情（跳转开发者中心）
                <AppIcon name="external-link" />
              </a>
            </div>
            <p v-if="actionError" class="publish-panel__error" role="alert">{{ actionError }}</p>
            <div class="publish-panel__actions">
              <button
                v-if="view === 'failed'"
                type="button"
                class="publish-panel__secondary"
                @click="close"
              >
                取消
              </button>
              <button
                type="button"
                class="publish-panel__primary"
                :disabled="submitting || !publication.latest_version_id"
                @click="submitDeployment"
              >
                {{ submitting ? '正在提交…' : '重试' }}
              </button>
            </div>
          </template>
        </template>
      </section>
    </template>
  </bk-popover>
</template>

<script setup lang="ts">
import { computed, onScopeDispose, ref, watch } from 'vue';
import { storeToRefs } from 'pinia';
import Message from '@/common/message';
import { getPublicationLinks } from '@/common/publication';
import AppIcon from '@/components/AppIcon.vue';
import { useAppNameValidate } from '@/composables/use-app-name-validate';
import { usePopoverVisible } from '@/composables/use-popover-visible';
import { usePublication } from '@/composables/use-publication';
import { useProjectStore } from '@/store/project';
import PublicationAppNameField from './PublicationAppNameField.vue';
import FailureBar from './PublicationFailureBar.vue';
import ManagedLinks from './PublicationManagedLinks.vue';
import OnlineDetails from './PublicationOnlineDetails.vue';

type PublicationView =
  | 'loading'
  | 'load-error'
  | 'form'
  | 'publishing'
  | 'success'
  | 'online'
  | 'failed'
  | 'failure-detail';

const PUBLISH_HELP = '发布会把当前工作区最新版本部署到蓝鲸开发者中心并生成公开访问地址，有新版本时可以继续更新。';

const { projectId } = storeToRefs(useProjectStore());
const {
  publication,
  loading,
  refreshing,
  submitting,
  loadError,
  actionError,
  conflictedAppName,
  isFirstPublication,
  hasNewVersion,
  pull,
  deployLatest,
  acknowledgeResult,
  clearActionError,
} = usePublication(projectId);
const appNameValidation = useAppNameValidate(projectId);
const {
  popoverRef,
  visible,
  onAfterShow,
  onAfterHidden,
  close,
} = usePopoverVisible();

const manualPage = ref<'failure' | null>(null);
const appName = ref('');
const copyDone = ref(false);
let appNameTouched = false;
let resultWasDisplayed = false;
let copyResetTimer = 0;

const publicationLinks = computed(() => getPublicationLinks(publication.value));
const appNamePending = computed(() => appNameValidation.isPending(appName.value));
const appNameResult = computed(() => appNameValidation.resultFor(appName.value));

const view = computed<PublicationView>(() => {
  const state = publication.value;
  if (!state) return loadError.value && !loading.value ? 'load-error' : 'loading';
  if (state.task) return 'publishing';
  if (state.unseen_result?.status === 'successful' && state.online) return 'success';
  if (state.unseen_result?.status === 'failed' && state.last_failure) return 'failed';
  if (manualPage.value === 'failure' && state.last_failure) return 'failure-detail';
  if (state.online) return 'online';
  return 'form';
});

const triggerLabel = computed(() => {
  const state = publication.value;
  if (state?.task) return '发布中…';
  if (state?.online) return '已发布';
  return '发布';
});

const canSubmit = computed(() => {
  const state = publication.value;
  if (!state?.latest_version_id || state.task || submitting.value) return false;
  if (!isFirstPublication.value) return true;

  // 首次发布要等名称检查完；检查接口失败时没有结论，不拦发布，由发布时的校验兜底。
  if (!appName.value.trim() || appNamePending.value) return false;
  return appNameResult.value?.is_available !== false;
});

const progressText = computed(() => {
  if (publication.value?.task?.stage === 'binding') {
    return '正在创建蓝鲸开发者中心应用，预计耗时 2 分钟，请耐心等待';
  }
  return '正在发布当前工作区最新版本，预计耗时 2 分钟，请耐心等待';
});

const handleAppNameInput = (name: string) => {
  appName.value = name;
  appNameTouched = true;
  clearActionError();
};

const submitDeployment = async () => {
  const started = await deployLatest(isFirstPublication.value ? appName.value : undefined);
  if (started) manualPage.value = null;
};

const copyText = async (text: string) => {
  if (window.isSecureContext && navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text);
    return;
  }
  const area = document.createElement('textarea');
  area.value = text;
  area.style.cssText = 'position:fixed;opacity:0;pointer-events:none;';
  document.body.appendChild(area);
  area.select();
  const copied = document.execCommand('copy');
  area.remove();
  if (!copied) throw new Error('copy failed');
};

const copyOnlineUrl = async () => {
  const url = publication.value?.online?.url;
  if (!url) return;
  try {
    await copyText(url);
    copyDone.value = true;
    window.clearTimeout(copyResetTimer);
    copyResetTimer = window.setTimeout(() => {
      copyDone.value = false;
    }, 1600);
    Message({ theme: 'success', message: '已复制访问地址', delay: 1200 });
  } catch {
    Message({ theme: 'error', message: '复制失败，请手动复制访问地址' });
  }
};

const handlePopoverShow = () => {
  manualPage.value = null;
  resultWasDisplayed = Boolean(publication.value?.unseen_result);
  onAfterShow();
  void pull(true);
};

const handlePopoverHidden = () => {
  onAfterHidden();
  manualPage.value = null;
  if (resultWasDisplayed) void acknowledgeResult();
  resultWasDisplayed = false;
};

watch(projectId, () => {
  appName.value = '';
  appNameTouched = false;
  resultWasDisplayed = false;
});

watch(() => publication.value?.default_app_name, (name) => {
  if (!appNameTouched) appName.value = name || '';
}, { immediate: true });

// 名称只在首次发布、面板开着时才需要检查：打开时立即问一次，改名时等用户停下来再问。
watch([visible, isFirstPublication], ([isVisible, isFirst]) => {
  if (isVisible && isFirst) appNameValidation.validate(appName.value, true);
});

watch(appName, (name) => {
  if (visible.value && isFirstPublication.value) appNameValidation.validate(name);
});

// 发布时开发者中心报了重名：直接按重名展示，名称输入框会随之进入编辑。
watch(conflictedAppName, (name) => {
  if (name) appNameValidation.markTaken(name);
});

watch(
  [visible, () => publication.value?.unseen_result],
  ([isVisible, unseen]) => {
    if (isVisible && unseen) resultWasDisplayed = true;
  },
);

onScopeDispose(() => window.clearTimeout(copyResetTimer));
</script>

<style lang="postcss" scoped>
.publish-trigger {
  position: relative;
  display: inline-flex;
  flex-shrink: 0;
  align-items: center;
  gap: 6px;
  height: 32px;
  padding: 0 14px;
  color: var(--accent);
  font-size: 13px;
  font-weight: 600;
  white-space: nowrap;
  background: transparent;
  border: 1px solid var(--accent);
  border-radius: 8px;
  cursor: pointer;
  transition: background-color 120ms ease, border-color 120ms ease, color 120ms ease;
}

.publish-trigger:hover,
.publish-trigger.is-open {
  color: var(--check);
  background: var(--accent-soft);
  border-color: var(--check);
}

.publish-trigger.is-online,
.publish-trigger.is-busy {
  color: var(--ink);
  border-color: #d6dce6;
}

.publish-trigger.is-online:hover,
.publish-trigger.is-busy:hover,
.publish-trigger.is-online.is-open,
.publish-trigger.is-busy.is-open {
  color: var(--ink);
  background: var(--subtle-bg);
  border-color: var(--accent-focus);
}

.publish-trigger :deep(.app-icon) {
  font-size: 14px;
}

.publish-trigger__dot {
  width: 7px;
  height: 7px;
  background: var(--publish);
  border-radius: 50%;
  box-shadow: 0 0 0 3px var(--publish-soft);
}

.publish-trigger.has-failure::after {
  position: absolute;
  top: -3px;
  right: -3px;
  width: 8px;
  height: 8px;
  content: "";
  background: var(--danger);
  border: 2px solid #fff;
  border-radius: 50%;
}

.publish-panel {
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  gap: 12px;
  width: 360px;
  padding: 14px 16px 16px;
  color: var(--ink);
  font-size: 13px;
  background: #fff;
  border-radius: 12px;
}

:global(.publish-demo-popover),
:global(.publish-demo-popover.bk-popover),
:global(.publish-demo-popover .bk-pop2-content) {
  padding: 0 !important;
  border-radius: 12px;
}

:global(.publish-demo-popover) {
  box-shadow: 0 12px 32px rgba(16, 22, 34, 0.14), 0 0 0 1px rgba(16, 22, 34, 0.05);
}

.publish-panel__head {
  display: flex;
  align-items: center;
  gap: 4px;
  min-height: 24px;
}

.publish-panel__head h3 {
  flex: 1;
  margin: 0;
  font-size: 14px;
  font-weight: 600;
}

.publish-panel__back,
.publish-panel__help {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  padding: 0;
  color: var(--faint);
  font-size: 15px;
  background: transparent;
  border: 0;
  border-radius: 6px;
}

.publish-panel__back {
  margin-left: -6px;
  color: var(--muted);
  cursor: pointer;
}

.publish-panel__back:hover {
  color: var(--ink);
  background: var(--hover-bg);
}

.publish-panel__help {
  margin-right: -4px;
  cursor: help;
}

.publish-panel__help:hover {
  color: var(--muted);
}

.publish-panel__desc {
  margin: -6px 0 0;
  color: var(--muted);
  font-size: 12px;
}

.publish-panel__field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.publish-panel__field-label {
  font-size: 12px;
  font-weight: 600;
}

.publish-panel__version {
  box-sizing: border-box;
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  height: 34px;
  padding: 0 12px;
  color: var(--muted);
  font-size: 13px;
  background: #f7f8fa;
  border: 1px solid var(--line);
  border-radius: 8px;
  cursor: not-allowed;
}

.publish-panel__version :deep(.app-icon) {
  color: var(--faint);
  font-size: 14px;
}

.publish-panel__empty {
  margin: 0;
  padding: 10px 12px;
  color: var(--faint);
  font-size: 12px;
  line-height: 1.5;
  background: var(--subtle-bg);
  border-radius: 8px;
}

.publish-panel__error {
  margin: 0;
  padding: 8px 10px;
  color: #8a2b2b;
  font-size: 12px;
  line-height: 1.5;
  background: var(--danger-soft);
  border-radius: 8px;
}

.publish-panel__primary,
.publish-panel__secondary {
  width: 100%;
  height: 34px;
  font-size: 13px;
  font-weight: 600;
  border: 0;
  border-radius: 8px;
  cursor: pointer;
  transition: background-color 120ms ease;
}

.publish-panel__primary {
  color: #fff;
  background: var(--accent);
}

.publish-panel__primary:hover:not(:disabled) {
  background: var(--check);
}

.publish-panel__primary:disabled,
.publish-panel__secondary:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}

.publish-panel__secondary {
  color: var(--ink);
  font-weight: 500;
  background: #f3f4f7;
}

.publish-panel__secondary:hover:not(:disabled) {
  background: #e8eaef;
}

.publish-panel__button-wrap {
  display: flex;
  cursor: not-allowed;
}

.publish-panel__button-wrap button:disabled {
  pointer-events: none;
}

.publish-panel__actions {
  display: flex;
  gap: 8px;
}

.publish-panel__status {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 12px 4px 4px;
  text-align: center;
}

.publish-panel__status h4 {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
}

.publish-panel__status p {
  max-width: 280px;
  margin: 0;
  color: var(--muted);
  font-size: 12px;
}

.publish-panel__spinner {
  display: inline-block;
  flex-shrink: 0;
  box-sizing: border-box;
  width: 36px;
  height: 36px;
  margin-bottom: 6px;
  color: var(--accent);
  border: 3px solid currentColor;
  border-right-color: transparent;
  border-radius: 50%;
  animation: publish-spin 0.8s linear infinite;
}

.publish-panel__spinner.is-small {
  width: 12px;
  height: 12px;
  margin: 0;
  border-width: 2px;
}

.publish-panel__status-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  margin-bottom: 4px;
  color: var(--danger);
  font-size: 22px;
  background: var(--danger-soft);
  border-radius: 50%;
}

.publish-panel__status-mark :deep(svg) {
  stroke-width: 2.6;
}

.publish-panel__status-note {
  color: var(--muted);
}

.publish-panel__failure-message {
  box-sizing: border-box;
  width: 100%;
  max-width: none !important;
  margin-top: 4px !important;
  padding: 8px 10px;
  color: #8a2b2b !important;
  font-family: var(--font-mono);
  line-height: 1.6;
  text-align: left;
  word-break: break-word;
  background: var(--danger-soft);
  border-radius: 8px;
}

.publish-panel__link {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  margin-top: 2px;
  color: var(--accent);
  font-size: 12px;
  text-decoration: none;
  border-radius: 4px;
}

.publish-panel__link:hover {
  text-decoration: underline;
  text-underline-offset: 3px;
}

.publish-panel__link :deep(.app-icon) {
  font-size: 11px;
}

.publish-panel__banner {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  background: #effaf3;
  border: 1px solid #cdeedb;
  border-radius: 10px;
  animation: publish-pop 0.3s ease-out;
}

.publish-panel__banner > span {
  display: inline-flex;
  flex: 0 0 30px;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  color: #fff;
  font-size: 16px;
  background: #14a568;
  border-radius: 50%;
}

.publish-panel__banner > span :deep(svg) {
  stroke-width: 3;
}

.publish-panel__banner strong {
  color: #146c43;
  font-size: 13px;
  font-weight: 600;
}

.publish-panel__banner p {
  margin: 1px 0 0;
  color: #3f7a5c;
  font-size: 12px;
}

.publish-trigger:focus-visible,
.publish-panel button:focus-visible,
.publish-panel a:focus-visible {
  outline: 2px solid var(--accent-focus);
  outline-offset: 2px;
}

@keyframes publish-spin {
  to { transform: rotate(360deg); }
}

@keyframes publish-pop {
  from {
    opacity: 0;
    transform: translateY(-4px);
  }

  to {
    opacity: 1;
    transform: none;
  }
}

@media (prefers-reduced-motion: reduce) {
  .publish-panel__spinner,
  .publish-panel__banner {
    animation: none;
  }
}
</style>
