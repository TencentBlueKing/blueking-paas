<template>
  <div class="project-switcher">
    <bk-popover
      ref="popoverRef"
      theme="light"
      placement="bottom-start"
      trigger="click"
      :arrow="false"
      :padding="0"
      :offset="4"
      ext-cls="project-switcher-popover"
      @after-show="handlePopoverShow"
      @after-hidden="handlePopoverHidden"
    >
      <button
        type="button"
        class="project-switcher__trigger"
        :class="{ 'is-open': visible }"
        aria-haspopup="menu"
        :aria-expanded="visible"
      >
        <span class="project-switcher__name">{{ currentName }}</span>
        <AppIcon class="project-switcher__arrow" name="chevron-down" />
      </button>
      <template #content>
        <div class="project-switcher__panel" role="menu">
          <div
            class="project-switcher__recent-owner"
            @mouseenter="showRecent()"
            @mouseleave="scheduleRecentHide"
            @focusin="showRecent()"
            @focusout="scheduleRecentHide"
          >
            <bk-popover
              trigger="manual"
              placement="right-start"
              theme="light"
              :is-show="recentVisible"
              :arrow="false"
              :padding="0"
              :offset="4"
              boundary="body"
              ext-cls="project-recent-popover"
            >
              <button
                ref="recentTriggerRef"
                type="button"
                class="project-switcher__action"
                role="menuitem"
                aria-haspopup="menu"
                :aria-expanded="recentVisible"
                @click="toggleRecent"
                @keydown.right.prevent="showRecent(true)"
              >
                <AppIcon name="clock" />
                <span>最近项目</span>
                <AppIcon class="project-switcher__chevron" name="chevron-right" />
              </button>
              <template #content>
                <div
                  ref="recentPanelRef"
                  class="project-switcher__submenu"
                  role="menu"
                  aria-label="最近项目"
                  @mouseenter="cancelRecentHide"
                  @mouseleave="scheduleRecentHide"
                  @focusin="cancelRecentHide"
                  @focusout="scheduleRecentHide"
                  @keydown.left.prevent="closeRecent(true)"
                  @keydown.esc.stop.prevent="closeRecent(true)"
                  @scroll.passive="handleRecentScroll"
                >
                  <div
                    v-if="recentLoading"
                    class="project-switcher__status is-loading"
                    role="status"
                  >
                    <span class="project-switcher__spinner" aria-hidden="true" />
                    加载中…
                  </div>
                  <div v-else-if="recentError" class="project-switcher__status is-error">
                    <span>{{ recentError }}</span>
                    <button type="button" class="project-switcher__retry" @click="fetchRecentProjects">
                      重试
                    </button>
                  </div>
                  <div v-else-if="!recentProjects.length" class="project-switcher__status">
                    暂无其他项目
                  </div>
                  <template v-else>
                    <button
                      v-for="item in recentProjects"
                      :key="item.id"
                      type="button"
                      class="project-switcher__row"
                      role="menuitem"
                      @click="handleSelect(item.id)"
                    >
                      <span>{{ item.name || item.id }}</span>
                      <time>{{ fromNowFormatter(item.updated_at) }}</time>
                    </button>
                    <div
                      v-if="recentLoadingMore"
                      class="project-switcher__status is-loading-more"
                      role="status"
                    >
                      <span class="project-switcher__spinner" aria-hidden="true" />
                      加载更多…
                    </div>
                    <div
                      v-else-if="recentLoadMoreError"
                      class="project-switcher__status is-error"
                    >
                      <span>{{ recentLoadMoreError }}</span>
                      <button
                        type="button"
                        class="project-switcher__retry"
                        @click="loadNextRecentPage"
                      >
                        重试
                      </button>
                    </div>
                  </template>
                </div>
              </template>
            </bk-popover>
          </div>
          <div class="project-switcher__separator" role="separator" />
          <button type="button" class="project-switcher__action" role="menuitem" @click="openRename">
            <AppIcon name="pencil" />
            <span>重命名</span>
          </button>
          <button
            type="button"
            class="project-switcher__action is-danger"
            role="menuitem"
            @click="openDelete"
          >
            <AppIcon name="trash" />
            <span>删除</span>
          </button>
        </div>
      </template>
    </bk-popover>

    <AppModal
      v-model="confirmVisible"
      title="确认离开当前项目吗？"
      description="如有进行中的操作，操作可能会被中止。"
      confirm-text="确定离开"
      @confirm="handleConfirm"
      @update:modelValue="onConfirmVisible"
    />

    <RenameProjectDialog
      v-model="renameVisible"
      :project="currentProject"
      @renamed="handleRenamed"
    />

    <DeleteProjectDialog
      v-model="deleteVisible"
      :project="deletingProject"
      @deleted="handleDeleted"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { useRouter } from 'vue-router';
import { storeToRefs } from 'pinia';
import Message from '@/common/message';
import { fromNowFormatter } from '@/common/util';
import AppIcon from '@/components/AppIcon.vue';
import AppModal from '@/components/project/AppModal.vue';
import DeleteProjectDialog from '@/components/project/DeleteProjectDialog.vue';
import RenameProjectDialog from '@/components/project/RenameProjectDialog.vue';
import { useHoverSubmenu } from '@/composables/use-hover-submenu';
import { usePopoverVisible } from '@/composables/use-popover-visible';
import { listProjects } from '@/http/api';
import type { ProjectResponse } from '@/http/types';
import { useProjectStore } from '@/store/project';

const router = useRouter();
const { projectId } = storeToRefs(useProjectStore());
const RECENT_PAGE_SIZE = 21;
const RECENT_LOAD_THRESHOLD = 48;
const currentProjectData = ref<ProjectResponse | null>(null);
const recentProjectItems = ref<ProjectResponse[]>([]);
const {
  popoverRef,
  visible,
  onAfterShow,
  onAfterHidden,
  close,
} = usePopoverVisible();
const confirmVisible = ref(false);
const pendingProjectId = ref('');
const renameVisible = ref(false);
const deleteVisible = ref(false);
const deletingProject = ref<ProjectResponse | null>(null);
const recentLoading = ref(false);
const recentLoadingMore = ref(false);
const recentError = ref('');
const recentLoadMoreError = ref('');
const recentCount = ref(0);
const recentPage = ref(0);
const hasMoreRecentProjects = computed(() => recentProjectItems.value.length < recentCount.value);
let currentProjectRequest = 0;
let recentLoadGeneration = 0;

const currentProject = computed<ProjectResponse | null>(() => {
  const current = currentProjectData.value?.id === projectId.value
    ? currentProjectData.value
    : null;
  if (current) return current;
  if (!projectId.value) return null;
  return {
    id: projectId.value,
    name: projectId.value,
    created_at: '',
    updated_at: '',
  };
});

const currentName = computed(() => currentProject.value?.name || '选择项目');

const recentProjects = computed(() => (
  recentProjectItems.value
    .filter(item => item.id !== projectId.value)
));

const handlePopoverShow = () => {
  onAfterShow();
  closeRecent();
};

const handlePopoverHidden = () => {
  onAfterHidden();
  closeRecent();
};

const fetchCurrentProject = async () => {
  const id = projectId.value;
  const request = ++currentProjectRequest;
  currentProjectData.value = null;
  if (!id) return;
  try {
    const data = await listProjects({ page: 1, page_size: 100 });
    if (request === currentProjectRequest && projectId.value === id) {
      currentProjectData.value = (data.items || []).find(item => item.id === id) ?? null;
    }
  } catch (error) {
    if (request !== currentProjectRequest || projectId.value !== id) return;
    Message({
      theme: 'error',
      message: error instanceof Error ? error.message : '获取项目信息失败',
    });
  }
};

const fetchRecentProjects = async () => {
  const generation = ++recentLoadGeneration;
  recentLoading.value = true;
  recentLoadingMore.value = false;
  recentError.value = '';
  recentLoadMoreError.value = '';
  recentProjectItems.value = [];
  recentCount.value = 0;
  recentPage.value = 0;
  try {
    const data = await listProjects({ page: 1, page_size: RECENT_PAGE_SIZE });
    if (generation !== recentLoadGeneration) return;
    recentProjectItems.value = data.items || [];
    recentCount.value = data.count || 0;
    recentPage.value = 1;
  } catch (error) {
    if (generation !== recentLoadGeneration) return;
    recentError.value = error instanceof Error ? error.message : '获取最近项目失败';
  } finally {
    if (generation === recentLoadGeneration) recentLoading.value = false;
  }
};

const loadNextRecentPage = async () => {
  if (recentLoading.value || recentLoadingMore.value || !hasMoreRecentProjects.value) return;
  const generation = recentLoadGeneration;
  const nextPage = recentPage.value + 1;
  recentLoadingMore.value = true;
  recentLoadMoreError.value = '';
  try {
    const data = await listProjects({ page: nextPage, page_size: RECENT_PAGE_SIZE });
    if (generation !== recentLoadGeneration) return;
    const knownIds = new Set(recentProjectItems.value.map(item => item.id));
    const additions = (data.items || []).filter(item => !knownIds.has(item.id));
    recentProjectItems.value = [...recentProjectItems.value, ...additions];
    recentCount.value = additions.length
      ? data.count || recentProjectItems.value.length
      : recentProjectItems.value.length;
    recentPage.value = nextPage;
  } catch (error) {
    if (generation !== recentLoadGeneration) return;
    recentLoadMoreError.value = error instanceof Error ? error.message : '加载更多项目失败';
  } finally {
    if (generation === recentLoadGeneration) recentLoadingMore.value = false;
  }
};

const handleRecentScroll = (event: Event) => {
  const panel = event.currentTarget as HTMLElement;
  const distanceToBottom = panel.scrollHeight - panel.scrollTop - panel.clientHeight;
  if (distanceToBottom <= RECENT_LOAD_THRESHOLD) void loadNextRecentPage();
};

const {
  triggerRef: recentTriggerRef,
  panelRef: recentPanelRef,
  visible: recentVisible,
  show: showRecent,
  close: closeRecent,
  toggle: toggleRecent,
  scheduleClose: scheduleRecentHide,
  cancelClose: cancelRecentHide,
} = useHoverSubmenu({ onOpen: fetchRecentProjects });

const handleSelect = (id: string) => {
  closeRecent();
  close();
  if (!id || id === projectId.value) return;
  pendingProjectId.value = id;
  confirmVisible.value = true;
};

const onConfirmVisible = (visible: boolean) => {
  if (!visible) pendingProjectId.value = '';
};

const handleConfirm = () => {
  const nextId = pendingProjectId.value;
  pendingProjectId.value = '';
  confirmVisible.value = false;
  if (!nextId || nextId === projectId.value) return;
  router.push({ name: 'project', params: { projectId: nextId } });
};

const openRename = () => {
  closeRecent();
  close();
  renameVisible.value = true;
};

const handleRenamed = (name: string) => {
  const current = currentProjectData.value;
  if (!current || current.id !== projectId.value) return;
  currentProjectData.value = { ...current, name };
};

const openDelete = () => {
  closeRecent();
  close();
  deletingProject.value = currentProject.value;
  deleteVisible.value = true;
};

const handleDeleted = () => {
  deleteVisible.value = false;
  deletingProject.value = null;
  router.replace({ name: 'projects' });
};

watch(projectId, fetchCurrentProject, { immediate: true });
</script>

<style lang="postcss" scoped>
.project-switcher__trigger {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  min-width: 0;
  max-width: 280px;
  height: 32px;
  padding: 0 6px 0 8px;
  color: var(--ink);
  cursor: pointer;
  background: transparent;
  border: 0;
  border-radius: 8px;
  transition: background-color 120ms ease;
}

.project-switcher__trigger:hover,
.project-switcher__trigger.is-open {
  background: #eef1f6;
}

.project-switcher__name {
  overflow: hidden;
  font-size: 15px;
  font-weight: 600;
  letter-spacing: -0.01em;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.project-switcher__arrow {
  flex-shrink: 0;
  color: var(--faint);
  font-size: 16px;
  transition: transform 160ms ease;
}

.project-switcher__trigger.is-open .project-switcher__arrow {
  transform: rotate(180deg);
}

.project-switcher__panel {
  box-sizing: border-box;
  width: 168px;
  padding: 6px;
  background: #fff;
  border-radius: 12px;
  box-shadow:
    0 12px 32px rgba(16, 22, 34, 0.14),
    0 0 0 1px rgba(16, 22, 34, 0.05);
}

.project-switcher__action {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  width: 100%;
  padding: 8px 10px;
  color: var(--ink);
  font-size: 13px;
  text-align: left;
  cursor: pointer;
  background: transparent;
  border: 0;
  border-radius: 8px;
}

.project-switcher__action:hover,
.project-switcher__action:focus-visible,
.project-switcher__action[aria-expanded="true"] {
  background: var(--subtle-bg);
  outline: none;
}

.project-switcher__action > :deep(.app-icon) {
  flex-shrink: 0;
  width: 15px;
  height: 15px;
  margin-top: 2px;
  color: var(--faint);
  font-size: 15px;
}

.project-switcher__action.is-danger,
.project-switcher__action.is-danger > :deep(.app-icon) {
  color: var(--danger);
}

.project-switcher__action.is-danger:hover,
.project-switcher__action.is-danger:focus-visible {
  background: var(--danger-soft);
}

.project-switcher__recent-owner,
.project-switcher__recent-owner :deep(.bk-popover) {
  display: block;
  width: 100%;
}

.project-switcher__chevron {
  flex-shrink: 0;
  margin: 2px -2px 0 auto;
  color: var(--faint);
  font-size: 14px;
}

.project-switcher__separator {
  height: 1px;
  margin: 4px 6px;
  background: var(--line);
}

.project-switcher__submenu {
  box-sizing: border-box;
  width: 248px;
  min-height: 56px;
  max-height: min(420px, calc(100vh - 16px));
  padding: 6px;
  overflow-y: auto;
  background: #fff;
  border-radius: 12px;
  box-shadow:
    0 12px 32px rgba(16, 22, 34, 0.14),
    0 0 0 1px rgba(16, 22, 34, 0.05);
}

.project-switcher__row {
  display: flex;
  align-items: baseline;
  gap: 12px;
  width: 100%;
  padding: 8px 10px;
  color: var(--ink);
  font-size: 13px;
  text-align: left;
  cursor: pointer;
  background: transparent;
  border: 0;
  border-radius: 8px;
}

.project-switcher__row:hover,
.project-switcher__row:focus-visible {
  background: var(--subtle-bg);
  outline: none;
}

.project-switcher__row > span {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.project-switcher__row > time {
  flex-shrink: 0;
  color: var(--faint);
  font-size: 12px;
  font-variant-numeric: tabular-nums;
}

.project-switcher__status {
  box-sizing: border-box;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  min-height: 44px;
  padding: 12px 10px;
  color: var(--muted);
  font-size: 13px;
  line-height: 1.5;
}

.project-switcher__status.is-error {
  color: var(--danger);
}

.project-switcher__status.is-loading-more {
  justify-content: center;
}

.project-switcher__spinner {
  display: inline-block;
  flex-shrink: 0;
  width: 12px;
  height: 12px;
  border: 2px solid currentColor;
  border-right-color: transparent;
  border-radius: 50%;
  animation: project-switcher-spin 0.8s linear infinite;
}

.project-switcher__retry {
  padding: 0;
  color: var(--accent);
  font-size: 13px;
  cursor: pointer;
  background: transparent;
  border: 0;
}

@keyframes project-switcher-spin {
  to {
    transform: rotate(360deg);
  }
}

.project-switcher__trigger:focus-visible,
.project-switcher__action:focus-visible,
.project-switcher__row:focus-visible {
  outline: 2px solid var(--accent-focus);
  outline-offset: -2px;
}
</style>

<style lang="postcss">
.project-switcher-popover,
.project-switcher-popover.bk-popover,
.project-switcher-popover .bk-pop2-content,
.project-recent-popover,
.project-recent-popover.bk-popover,
.project-recent-popover .bk-pop2-content {
  padding: 0 !important;
  background: transparent !important;
  border: 0 !important;
  box-shadow: none !important;
}
</style>
