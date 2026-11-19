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
        :class="{
          'is-open': visible,
          'is-naming': namingVisual === 'shimmer',
          'is-named': namingVisual === 'named',
        }"
        :title="triggerTitle"
        aria-haspopup="menu"
        :aria-expanded="visible"
      >
        <span
          class="project-switcher__name"
          :class="{ 'has-caret': namingVisual === 'typing' }"
        >
          {{ displayName }}
        </span>
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
          <button
            type="button"
            class="project-switcher__action"
            role="menuitem"
            :disabled="autoNamingActive"
            :title="autoNamingActive ? 'AI 正在命名，完成后可重命名' : undefined"
            @click="openRename"
          >
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

    <Transition name="naming-hint">
      <span
        v-if="namingHint"
        class="project-switcher__naming-hint"
        :class="{ 'is-warning': namingHint.tone === 'warning' }"
        role="status"
      >
        <AppIcon :name="namingHint.tone === 'warning' ? 'alert-triangle' : 'sparkles'" />
        {{ namingHint.text }}
      </span>
    </Transition>

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
import { computed, onUnmounted, ref, watch } from 'vue';
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
const projectStore = useProjectStore();
const { intRenamingStatus, projectId, projectName } = storeToRefs(projectStore);
const RECENT_PAGE_SIZE = 21;
const RECENT_LOAD_THRESHOLD = 48;
const NAMING_START_DELAY = 700;
const NAMING_ERASE_STEP = 22;
const NAMING_TYPE_STEP = 70;
const NAMING_HIGHLIGHT_DURATION = 1600;
const NAMING_HINT_DURATION = 3200;
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
type NamingVisual = 'idle' | 'waiting' | 'shimmer' | 'typing' | 'named';
type NamingHint = { text: string; tone: 'success' | 'warning' };
const displayName = ref('选择项目');
const namingVisual = ref<NamingVisual>('idle');
const namingHint = ref<NamingHint | null>(null);
const namingTimers = new Set<ReturnType<typeof setTimeout>>();
let namingStartedAt = 0;
const hasMoreRecentProjects = computed(() => recentProjectItems.value.length < recentCount.value);
let currentProjectRequest = 0;
let recentLoadGeneration = 0;

const currentProject = computed<ProjectResponse | null>(() => {
  const current = currentProjectData.value?.id === projectId.value
    ? currentProjectData.value
    : null;
  if (current) {
    return projectName.value && projectName.value !== current.name
      ? { ...current, name: projectName.value }
      : current;
  }
  if (!projectId.value) return null;
  return {
    id: projectId.value,
    name: projectName.value || projectId.value,
    created_at: '',
    updated_at: '',
  };
});

const currentName = computed(() => currentProject.value?.name || '选择项目');
const autoNamingActive = computed(() => (
  intRenamingStatus.value === 'pending'
  || namingVisual.value === 'waiting'
  || namingVisual.value === 'shimmer'
  || namingVisual.value === 'typing'
));
const triggerTitle = computed(() => (
  autoNamingActive.value ? 'AI 正在根据你的描述命名…' : displayName.value
));

const scheduleNaming = (callback: () => void, delay: number) => {
  const timer = setTimeout(() => {
    namingTimers.delete(timer);
    callback();
  }, delay);
  namingTimers.add(timer);
};

const clearNamingTimers = () => {
  namingTimers.forEach(timer => clearTimeout(timer));
  namingTimers.clear();
};

const showNamingHint = (text: string, tone: NamingHint['tone']) => {
  namingHint.value = { text, tone };
  scheduleNaming(() => {
    namingHint.value = null;
  }, NAMING_HINT_DURATION);
};

const finishNamingAnimation = (name: string) => {
  displayName.value = name;
  namingVisual.value = 'named';
  showNamingHint('已根据对话命名', 'success');
  scheduleNaming(() => {
    namingStartedAt = 0;
    namingVisual.value = 'idle';
    displayName.value = currentName.value;
  }, NAMING_HIGHLIGHT_DURATION);
};

const retypeProjectName = (name: string) => {
  namingVisual.value = 'typing';
  let text = displayName.value;
  const erase = () => {
    if (text.length) {
      text = text.slice(0, -1);
      displayName.value = text;
      scheduleNaming(erase, NAMING_ERASE_STEP);
      return;
    }
    let index = 0;
    const type = () => {
      index += 1;
      displayName.value = name.slice(0, index);
      if (index < name.length) {
        scheduleNaming(type, NAMING_TYPE_STEP);
        return;
      }
      finishNamingAnimation(name);
    };
    type();
  };
  erase();
};

const resetNamingVisual = () => {
  clearNamingTimers();
  namingStartedAt = 0;
  namingVisual.value = 'idle';
  namingHint.value = null;
  displayName.value = currentName.value;
};

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
      const current = (data.items || []).find(item => item.id === id) ?? null;
      currentProjectData.value = current;
      if (current && !projectName.value) {
        projectStore.setProjectName(id, current.name);
      }
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
  if (autoNamingActive.value) return;
  closeRecent();
  close();
  renameVisible.value = true;
};

const handleRenamed = (renamed: ProjectResponse) => {
  if (renamed.id !== projectId.value) return;
  currentProjectData.value = renamed;
  projectStore.setProjectName(renamed.id, renamed.name);
  resetNamingVisual();
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

watch(currentName, (name) => {
  if (
    namingStartedAt === 0
    && namingVisual.value === 'idle'
    && intRenamingStatus.value !== 'pending'
  ) {
    displayName.value = name;
  }
}, { immediate: true });

watch(intRenamingStatus, (status, previous) => {
  if (status === 'pending') {
    clearNamingTimers();
    namingStartedAt = Date.now();
    namingVisual.value = 'waiting';
    namingHint.value = null;
    displayName.value = projectId.value || currentName.value;
    scheduleNaming(() => {
      if (intRenamingStatus.value === 'pending') namingVisual.value = 'shimmer';
    }, NAMING_START_DELAY);
    return;
  }

  if (status === 'completed' && previous === 'pending') {
    clearNamingTimers();
    const wait = Math.max(0, NAMING_START_DELAY - (Date.now() - namingStartedAt));
    scheduleNaming(() => retypeProjectName(currentName.value), wait);
    return;
  }

  if (status === 'failed' && previous === 'pending') {
    clearNamingTimers();
    namingStartedAt = 0;
    namingVisual.value = 'idle';
    displayName.value = currentName.value;
    showNamingHint('自动命名失败，可点击项目名重命名', 'warning');
    return;
  }

  if (status === 'idle' && previous === 'pending') resetNamingVisual();
}, { immediate: true });

watch(projectId, () => {
  resetNamingVisual();
  void fetchCurrentProject();
}, { immediate: true });

onUnmounted(clearNamingTimers);
</script>

<style lang="postcss" scoped>
.project-switcher {
  position: relative;
  min-width: 0;
}

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
  transition: background-color 120ms ease, box-shadow 200ms ease;
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

.project-switcher__trigger.is-naming {
  background: #f4f1ff;
  box-shadow: inset 0 0 0 1px #ddd5ff;
}

.project-switcher__trigger.is-naming .project-switcher__name {
  color: transparent;
  background: linear-gradient(90deg, #9aa3b2 0%, #7c5cff 42%, #ff5f8f 55%, #9aa3b2 100%);
  background-clip: text;
  background-size: 250% 100%;
  animation: naming-shimmer 1.2s linear infinite;
  -webkit-background-clip: text;
}

.project-switcher__name.has-caret {
  color: var(--ink);
  background: none;
  animation: none;
}

.project-switcher__name.has-caret::after {
  display: inline-block;
  width: 2px;
  height: 15px;
  margin-left: 2px;
  vertical-align: -2px;
  content: "";
  background: #7c5cff;
  animation: naming-caret-blink 0.8s steps(1) infinite;
}

.project-switcher__trigger.is-named {
  animation: naming-complete-glow 1.6s ease-out;
}

.project-switcher__naming-hint {
  position: absolute;
  top: calc(100% + 6px);
  left: 4px;
  z-index: 5;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  color: #6b4fd8;
  font-size: 12px;
  white-space: nowrap;
  background: #fff;
  border: 1px solid #e4ddff;
  border-radius: 999px;
  box-shadow: 0 6px 16px rgba(16, 22, 34, 0.08);
}

.project-switcher__naming-hint.is-warning {
  color: #a15c00;
  background: #fffaf0;
  border-color: #ffe0a3;
}

.project-switcher__naming-hint :deep(.app-icon) {
  font-size: 13px;
}

.naming-hint-enter-active {
  transition: opacity 240ms ease-out, transform 240ms ease-out;
}

.naming-hint-leave-active {
  transition: opacity 400ms ease;
}

.naming-hint-enter-from {
  opacity: 0;
  transform: translateY(-4px);
}

.naming-hint-leave-to {
  opacity: 0;
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

.project-switcher__action:disabled,
.project-switcher__action:disabled:hover,
.project-switcher__action:disabled:focus-visible {
  cursor: not-allowed;
  background: transparent;
  opacity: 0.6;
  outline: none;
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

@keyframes naming-shimmer {
  from {
    background-position: 100% 0;
  }

  to {
    background-position: -150% 0;
  }
}

@keyframes naming-caret-blink {
  50% {
    opacity: 0;
  }
}

@keyframes naming-complete-glow {
  0% {
    background: #f4f1ff;
    box-shadow: 0 0 0 3px rgba(124, 92, 255, 0.35);
  }

  100% {
    background: transparent;
    box-shadow: 0 0 0 0 rgba(124, 92, 255, 0);
  }
}

.project-switcher__trigger:focus-visible,
.project-switcher__action:focus-visible,
.project-switcher__row:focus-visible {
  outline: 2px solid var(--accent-focus);
  outline-offset: -2px;
}

@media (prefers-reduced-motion: reduce) {
  .project-switcher__trigger.is-naming .project-switcher__name,
  .project-switcher__name.has-caret::after,
  .project-switcher__trigger.is-named {
    animation: none;
  }

  .naming-hint-enter-active,
  .naming-hint-leave-active {
    transition: none;
  }
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
