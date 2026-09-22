<template>
  <div class="project-switcher">
    <bk-popover
      v-model:isShow="visible"
      theme="light"
      placement="bottom-start"
      trigger="click"
      :arrow="false"
      :padding="0"
      :offset="4"
      ext-cls="project-switcher-popover"
      @after-show="fetchProjects"
    >
      <div class="project-switcher__trigger" :class="{ 'is-open': visible }">
        <span class="project-switcher__name">{{ currentName }}</span>
        <AngleDown class="project-switcher__arrow" />
      </div>
      <template #content>
        <div class="project-switcher__panel">
          <div class="project-switcher__search">
            <Search class="project-switcher__search-icon" />
            <input
              v-model="keyword"
              class="project-switcher__search-input"
              placeholder="输入项目名称搜索"
            >
          </div>
          <ul class="project-switcher__list">
            <li
              v-for="item in filteredProjects"
              :key="item.id"
              :class="[
                'project-switcher__item',
                { 'is-selected': item.id === projectId },
              ]"
              @click="handleSelect(item.id)"
            >
              <span class="project-switcher__item-name">{{ item.name || item.id }}</span>
              <span class="project-switcher__item-tag">{{ item.id }}</span>
            </li>
            <li v-if="!filteredProjects.length" class="project-switcher__empty">
              没有匹配的项目
            </li>
          </ul>
          <div class="project-switcher__footer" @click="openCreate">
            <Plus class="project-switcher__footer-icon" />
            新建项目
          </div>
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

    <CreateProjectDialog
      v-model="createVisible"
      @created="enterCreated"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import { storeToRefs } from 'pinia';
import { Message } from 'bkui-vue';
import { AngleDown, Plus, Search } from 'bkui-vue/lib/icon';
import AppModal from '@/components/project/AppModal.vue';
import CreateProjectDialog from '@/components/project/CreateProjectDialog.vue';
import { listProjects } from '@/http/api';
import type { ProjectResponse } from '@/http/types';
import { useProjectStore } from '@/store/project';

const router = useRouter();
const { projectId } = storeToRefs(useProjectStore());
const projects = ref<ProjectResponse[]>([]);
const keyword = ref('');
const visible = ref(false);
const confirmVisible = ref(false);
const createVisible = ref(false);
const pendingProjectId = ref('');

const currentName = computed(() => {
  const current = projects.value.find(item => item.id === projectId.value);
  return current?.name || projectId.value || '选择项目';
});

const filteredProjects = computed(() => {
  const text = keyword.value.trim().toLowerCase();
  if (!text) return projects.value;
  return projects.value.filter(item => (
    item.name.toLowerCase().includes(text) || item.id.toLowerCase().includes(text)
  ));
});

const fetchProjects = async () => {
  try {
    const data = await listProjects({ page: 1, page_size: 100 });
    projects.value = data.items || [];
    if (projectId.value && !projects.value.some(item => item.id === projectId.value)) {
      projects.value.unshift({
        id: projectId.value,
        name: projectId.value,
        created_at: '',
        updated_at: '',
      });
    }
  } catch (error) {
    Message({
      theme: 'error',
      message: error instanceof Error ? error.message : '获取项目列表失败',
    });
  }
};

const handleSelect = (id: string) => {
  visible.value = false;
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

const openCreate = () => {
  visible.value = false;
  createVisible.value = true;
};

const enterCreated = (created: ProjectResponse) => {
  router.push({ name: 'project', params: { projectId: created.id } });
};

onMounted(fetchProjects);
</script>

<style lang="postcss" scoped>
.project-switcher__trigger {
  display: flex;
  align-items: center;
  min-width: 160px;
  max-width: 260px;
  height: 32px;
  padding: 0 10px;
  color: #fff;
  cursor: pointer;
  background: #1e252f;
  border: 1px solid #3a414c;
  border-radius: 2px;
}

.project-switcher__trigger.is-open {
  border-color: #3a84ff;
}

.project-switcher__name {
  flex: 1;
  overflow: hidden;
  font-size: 13px;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.project-switcher__arrow {
  margin-left: 8px;
  color: #c4c6cc;
  font-size: 16px;
}

.project-switcher__panel {
  width: 280px;
  overflow: hidden;
  background: #1b2129;
  border: 1px solid #3a414c;
  border-radius: 2px;
}

.project-switcher__search {
  display: flex;
  align-items: center;
  height: 40px;
  padding: 0 12px;
  border-bottom: 1px solid #2d3540;
}

.project-switcher__search-icon {
  margin-right: 8px;
  color: #979ba5;
  font-size: 14px;
}

.project-switcher__search-input {
  flex: 1;
  color: #dcdee5;
  font-size: 12px;
  background: transparent;
  border: none;
  outline: none;
}

.project-switcher__search-input::placeholder {
  color: #63656e;
}

.project-switcher__list {
  max-height: 240px;
  margin: 0;
  padding: 4px 0;
  overflow: auto;
  list-style: none;
}

.project-switcher__item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 36px;
  padding: 0 12px;
  color: #c4c6cc;
  cursor: pointer;
}

.project-switcher__item:hover {
  background: #242c38;
}

.project-switcher__item.is-selected {
  color: #3a84ff;
  background: #2a3a55;
}

.project-switcher__item-name {
  flex: 1;
  overflow: hidden;
  font-size: 13px;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.project-switcher__item-tag {
  flex-shrink: 0;
  margin-left: 8px;
  padding: 0 6px;
  color: #c4c6cc;
  font-size: 12px;
  line-height: 18px;
  background: #3a414c;
  border-radius: 2px;
}

.project-switcher__item.is-selected .project-switcher__item-tag {
  color: #dcdee5;
}

.project-switcher__empty {
  padding: 16px 12px;
  color: #63656e;
  font-size: 12px;
  text-align: center;
}

.project-switcher__footer {
  display: flex;
  align-items: center;
  height: 40px;
  padding: 0 12px;
  color: #dcdee5;
  font-size: 13px;
  cursor: pointer;
  border-top: 1px solid #2d3540;
}

.project-switcher__footer:hover {
  color: #3a84ff;
  background: #242c38;
}

.project-switcher__footer-icon {
  margin-right: 6px;
  font-size: 14px;
}
</style>

<style lang="postcss">
.project-switcher-popover,
.project-switcher-popover.bk-popover,
.project-switcher-popover .bk-pop2-content {
  padding: 0 !important;
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
}
</style>
