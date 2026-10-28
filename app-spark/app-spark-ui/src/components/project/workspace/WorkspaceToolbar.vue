<template>
  <div class="workspace-toolbar">
    <div class="workspace-toolbar__seg" role="tablist" aria-label="视图">
      <button type="button" role="tab" aria-selected="true">预览</button>
    </div>

    <div class="workspace-toolbar__actions">
      <PublishDemo />
      <bk-popover
        trigger="click"
        placement="bottom-end"
        theme="light"
        :arrow="false"
        :padding="0"
        :offset="6"
        ext-cls="workspace-action-popover"
      >
        <button class="workspace-toolbar__more" type="button" aria-label="更多操作">
          <AppIcon name="more" />
        </button>
        <template #content>
          <div class="workspace-action-menu" role="menu">
            <a
              v-if="archiveUrl"
              class="workspace-action-menu__item"
              :href="archiveUrl"
              target="_blank"
              rel="noopener"
              role="menuitem"
            >
              <AppIcon name="download" />
              <span class="workspace-action-menu__text">
                <span>下载源码</span>
                <small>主分支源码，不含本轮尚未保存的改动</small>
              </span>
            </a>
            <button v-else class="workspace-action-menu__item" type="button" role="menuitem" disabled>
              <AppIcon name="download" />
              <span class="workspace-action-menu__text">
                <span>下载源码</span>
                <small>主分支源码，不含本轮尚未保存的改动</small>
              </span>
            </button>
          </div>
        </template>
      </bk-popover>
    </div>
  </div>
</template>

<script setup lang="ts">
import { storeToRefs } from 'pinia';
import { useSourceArchive } from '@/composables/use-source-archive';
import { useProjectStore } from '@/store/project';
import AppIcon from '@/components/AppIcon.vue';
import PublishDemo from './PublishDemo.vue';

const { projectId } = storeToRefs(useProjectStore());
const { archiveUrl } = useSourceArchive(projectId);
</script>

<style lang="postcss" scoped>
.workspace-toolbar {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: space-between;
  height: var(--rail-h);
  padding: 0 16px;
  background: #fff;
  border-bottom: 1px solid var(--line);
}

.workspace-toolbar__seg {
  display: inline-flex;
  padding: 3px;
  background: #f3f4f7;
  border-radius: 10px;
}

.workspace-toolbar__seg button {
  height: 28px;
  padding: 0 12px;
  color: var(--ink);
  font-size: 13px;
  font-weight: 600;
  background: #fff;
  border: 0;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(18, 28, 48, 0.08);
}

.workspace-toolbar__actions {
  display: flex;
  align-items: center;
  gap: 6px;
}

.workspace-toolbar__more {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  padding: 0;
  color: var(--faint);
  background: transparent;
  border: 0;
  border-radius: 8px;
  cursor: pointer;
}

.workspace-toolbar__more:hover {
  color: var(--ink);
  background: var(--hover-bg);
}

.workspace-toolbar__more :deep(.app-icon) {
  font-size: 18px;
}

.workspace-action-menu {
  box-sizing: border-box;
  width: 268px;
  padding: 6px;
  background: #fff;
  border-radius: 12px;
}

:global(.workspace-action-popover) {
  border-radius: 12px;
  box-shadow: 0 12px 32px rgba(16, 22, 34, 0.14), 0 0 0 1px rgba(16, 22, 34, 0.05);
}

.workspace-action-menu__item {
  box-sizing: border-box;
  display: flex;
  align-items: flex-start;
  gap: 10px;
  width: 100%;
  padding: 8px 10px;
  color: var(--ink);
  font-size: 13px;
  line-height: 1.5;
  text-align: left;
  text-decoration: none;
  background: #fff;
  border: 0;
  border-radius: 8px;
  cursor: pointer;
}

.workspace-action-menu__item :deep(.app-icon) {
  flex: 0 0 15px;
  width: 15px;
  height: 15px;
  margin-top: 2px;
  color: var(--faint);
}

.workspace-action-menu__text {
  min-width: 0;
}

.workspace-action-menu__text small {
  display: block;
  margin-top: 2px;
  color: var(--faint);
  font-size: 12px;
  white-space: nowrap;
}

.workspace-action-menu__item:hover:not(:disabled),
.workspace-action-menu__item:focus-visible {
  background: var(--subtle-bg);
  outline: none;
}

.workspace-action-menu__item:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.workspace-toolbar__more:focus-visible {
  outline: 2px solid var(--accent-focus);
  outline-offset: 2px;
}
</style>
