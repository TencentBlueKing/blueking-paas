<template>
  <bk-popover
    ref="popoverRef"
    trigger="click"
    placement="bottom-end"
    theme="light"
    :arrow="false"
    :padding="0"
    ext-cls="publish-demo-popover"
    @after-show="onAfterShow"
    @after-hidden="handlePopoverHidden"
  >
    <button type="button" class="publish-trigger">
      <AppIcon name="globe" />
      <span>发布</span>
    </button>
    <template #content>
      <section class="publish-panel" aria-label="发布项目">
        <header class="publish-panel__head">
          <h3>发布项目</h3>
        </header>
        <p class="publish-panel__desc">发布以获取可分享的公开访问地址。</p>

        <div v-if="state === 'form'" class="publish-panel__body">
          <div class="publish-panel__field">
            <span class="publish-panel__field-label">版本</span>
            <span
              ref="versionSelectRef"
              class="publish-panel__select"
              @keydown.esc.stop.prevent="versionMenuOpen = false"
            >
              <button
                type="button"
                class="publish-panel__select-trigger"
                :class="{ 'is-open': versionMenuOpen }"
                aria-haspopup="listbox"
                :aria-expanded="versionMenuOpen"
                aria-controls="publish-version-options"
                @click="versionMenuOpen = !versionMenuOpen"
              >
                <span>{{ selectedVersionLabel }}</span>
                <AppIcon name="chevron-down" />
              </button>
              <span
                v-if="versionMenuOpen"
                id="publish-version-options"
                class="publish-panel__select-menu"
                role="listbox"
                aria-label="发布版本"
              >
                <button
                  type="button"
                  role="option"
                  :aria-selected="selectedVersion === 'latest'"
                  @click="selectVersion('latest')"
                >
                  <span class="publish-panel__option-check">
                    <AppIcon v-if="selectedVersion === 'latest'" name="check" />
                  </span>
                  <span>当前工作区最新版本</span>
                </button>
                <span class="publish-panel__option-group">之前的版本</span>
                <button
                  type="button"
                  role="option"
                  :aria-selected="selectedVersion === 'v1'"
                  @click="selectVersion('v1')"
                >
                  <span class="publish-panel__option-check">
                    <AppIcon v-if="selectedVersion === 'v1'" name="check" />
                  </span>
                  <span>v1 · 首次生成</span>
                </button>
              </span>
            </span>
          </div>
          <button type="button" class="publish-panel__primary" @click="startDemo">发布</button>
        </div>

        <div v-else-if="state === 'publishing'" class="publish-panel__status">
          <span class="publish-panel__spinner" aria-hidden="true" />
          <h4>正在发布应用</h4>
          <p>正在准备运行环境与应用版本…</p>
          <button type="button" @click="cancelDemo">取消</button>
        </div>

        <div v-else-if="state === 'online'" class="publish-panel__status is-success">
          <span class="publish-panel__check" aria-hidden="true">
            <AppIcon name="check" />
          </span>
          <h4>项目已成功发布</h4>
          <p>访问地址准备完成后会显示在这里。</p>
          <div class="publish-panel__status-actions">
            <button type="button" @click="state = 'form'">返回</button>
            <button type="button" class="is-danger" @click="startUnpublishDemo">下架</button>
          </div>
        </div>

        <div v-else class="publish-panel__status">
          <span class="publish-panel__spinner" aria-hidden="true" />
          <h4>正在下架应用</h4>
          <p>下架完成后，公开访问地址将失效。</p>
          <button type="button" @click="cancelUnpublishDemo">取消</button>
        </div>
      </section>
    </template>
  </bk-popover>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import AppIcon from '@/components/AppIcon.vue';
import { usePopoverVisible } from '@/composables/use-popover-visible';

const {
  popoverRef,
  onAfterShow,
  onAfterHidden: markPopoverHidden,
} = usePopoverVisible();
const state = ref<'form' | 'publishing' | 'online' | 'unpublishing'>('form');
const versionSelectRef = ref<HTMLElement>();
const versionMenuOpen = ref(false);
const selectedVersion = ref<'latest' | 'v1'>('latest');
const selectedVersionLabel = computed(() => (
  selectedVersion.value === 'latest' ? '当前工作区最新版本' : 'v1 · 首次生成'
));
let timer = 0;

const selectVersion = (version: 'latest' | 'v1') => {
  selectedVersion.value = version;
  versionMenuOpen.value = false;
};

const handleDocumentPointerDown = (event: PointerEvent) => {
  if (!versionSelectRef.value?.contains(event.target as Node)) {
    versionMenuOpen.value = false;
  }
};

const handlePopoverHidden = () => {
  versionMenuOpen.value = false;
  markPopoverHidden();
};

const startDemo = () => {
  state.value = 'publishing';
  window.clearTimeout(timer);
  timer = window.setTimeout(() => {
    state.value = 'online';
  }, 1600);
};

const cancelDemo = () => {
  window.clearTimeout(timer);
  state.value = 'form';
};

const startUnpublishDemo = () => {
  state.value = 'unpublishing';
  window.clearTimeout(timer);
  timer = window.setTimeout(() => {
    state.value = 'form';
  }, 1400);
};

const cancelUnpublishDemo = () => {
  window.clearTimeout(timer);
  state.value = 'online';
};

onMounted(() => document.addEventListener('pointerdown', handleDocumentPointerDown));

onBeforeUnmount(() => {
  window.clearTimeout(timer);
  document.removeEventListener('pointerdown', handleDocumentPointerDown);
});
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

.publish-trigger:hover {
  color: var(--check);
  background: var(--accent-soft);
  border-color: var(--check);
}

.publish-trigger :deep(.app-icon) {
  font-size: 14px;
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
}

:global(.publish-demo-popover) {
  border-radius: 12px;
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

.publish-panel__desc {
  margin: -6px 0 0;
  color: var(--muted);
  font-size: 12px;
}

.publish-panel__body {
  display: flex;
  flex-direction: column;
  gap: 12px;
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

.publish-panel__select {
  position: relative;
  display: block;
}

.publish-panel__select-trigger {
  box-sizing: border-box;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  width: 100%;
  height: 34px;
  padding: 0 32px 0 12px;
  color: var(--ink);
  font-size: 13px;
  text-align: left;
  cursor: pointer;
  background: #f7f8fa;
  border: 1px solid var(--line);
  border-radius: 8px;
}

.publish-panel__select-trigger:hover {
  border-color: #cfd6e2;
}

.publish-panel__select-trigger.is-open {
  background: #fff;
  border-color: var(--accent-focus);
}

.publish-panel__select-trigger :deep(.app-icon) {
  position: absolute;
  top: 50%;
  right: 10px;
  color: var(--faint);
  font-size: 14px;
  pointer-events: none;
  transform: translateY(-50%);
}

.publish-panel__select-menu {
  position: absolute;
  top: calc(100% + 4px);
  right: 0;
  left: 0;
  z-index: 3;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  padding: 4px;
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 8px;
  box-shadow: 0 10px 24px rgba(16, 22, 34, 0.16);
}

.publish-panel__select-menu button {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;
  height: 34px;
  padding: 0 8px;
  color: var(--ink);
  font-size: 13px;
  text-align: left;
  background: transparent;
  border: 0;
  border-radius: 6px;
  cursor: pointer;
}

.publish-panel__select-menu button:hover {
  background: var(--hover-bg);
}

.publish-panel__select-menu button[aria-selected="true"] {
  color: #fff;
  background: var(--accent);
}

.publish-panel__option-check {
  display: inline-flex;
  flex: 0 0 16px;
  align-items: center;
  justify-content: center;
}

.publish-panel__option-check :deep(.app-icon) {
  font-size: 15px;
}

.publish-panel__option-group {
  padding: 5px 8px 3px 30px;
  color: var(--faint);
  font-size: 12px;
}

.publish-panel__primary {
  width: 100%;
  height: 34px;
  color: #fff;
  font-size: 13px;
  font-weight: 600;
  background: var(--accent);
  border: 0;
  border-radius: 8px;
  cursor: pointer;
  transition: background-color 120ms ease;
}

.publish-panel__primary:hover {
  background: var(--check);
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

.publish-panel__status button {
  margin-top: 4px;
  padding: 0;
  color: var(--accent);
  font-size: 12px;
  background: transparent;
  border: 0;
  cursor: pointer;
}

.publish-panel__status-actions {
  display: flex;
  gap: 12px;
}

.publish-panel__status button.is-danger {
  color: var(--danger);
}

.publish-panel__spinner,
.publish-panel__check {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
}

.publish-panel__spinner {
  box-sizing: border-box;
  width: 36px;
  height: 36px;
  margin-bottom: 6px;
  border: 3px solid #dfe5f2;
  border-top-color: var(--accent);
  animation: publish-spin 0.9s linear infinite;
}

.publish-panel__check {
  width: 44px;
  height: 44px;
  margin-bottom: 4px;
  color: #14a568;
  background: #e4faf0;
}

.publish-panel__check :deep(.app-icon) {
  width: 22px;
  height: 22px;
  font-size: 22px;
}

.publish-trigger:focus-visible,
.publish-panel button:focus-visible {
  outline: 2px solid var(--accent-focus);
  outline-offset: 2px;
}

.publish-panel__select-trigger:focus-visible {
  border-color: var(--accent-focus);
  outline: none;
}

.publish-panel__select-menu button:focus-visible {
  outline-offset: -2px;
}

@keyframes publish-spin {
  to { transform: rotate(360deg); }
}

@media (prefers-reduced-motion: reduce) {
  .publish-panel__spinner {
    animation: none;
  }
}
</style>
