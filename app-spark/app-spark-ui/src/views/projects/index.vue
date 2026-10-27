<template>
  <HomeLayout>
    <div class="projects-page">
      <div class="projects-page__inner">
      <header class="projects-page__head">
        <h1>
          项目列表
          <span v-if="!loading" class="count-chip" :aria-label="`共 ${pagination.count} 个项目`">
            {{ pagination.count }}
          </span>
        </h1>
        <button type="button" class="projects-page__create" @click="createProject">
          <AppIcon name="plus-line" />
          创建新项目
        </button>
      </header>

      <div v-if="loading" class="project-rows" aria-busy="true">
        <div v-for="index in 6" :key="index" class="skeleton-row">
          <i /><i /><i />
        </div>
      </div>
      <div v-else-if="listError && !projects.length" class="list-state" role="alert">
        <h2>项目列表没有加载出来</h2>
        <p>{{ listError }}</p>
        <button type="button" class="projects-page__create" @click="fetchProjects">重试</button>
      </div>
      <div v-else-if="!projects.length" class="list-state">
        <h2>还没有项目</h2>
        <p>在首页描述你的想法，AI 会帮你把它做成一个应用。</p>
        <button type="button" class="projects-page__create" @click="createProject">
          创建第一个项目
        </button>
      </div>
      <template v-else>
        <p v-if="listError" class="inline-error" role="alert">
          {{ listError }}
          <button type="button" @click="fetchProjects">重试</button>
        </p>
        <ul class="project-rows">
          <li v-for="project in projects" :key="project.id" class="project-row">
            <button
              type="button"
              class="project-row__open"
              :aria-label="`进入项目 ${project.name}`"
              @click="enterProject(project)"
            >
              <span class="project-row__main">
                <strong :title="project.name">{{ project.name }}</strong>
                <code>{{ project.id }}</code>
              </span>
              <time
                :datetime="project.updated_at"
                :title="timeFormatter(project.updated_at, 'YYYY-MM-DD HH:mm')"
              >
                更新于 {{ fromNowFormatter(project.updated_at) }}
              </time>
            </button>
            <div class="project-row__actions">
              <ProjectActionsMenu
                @rename="openRename(project)"
                @delete="openDelete(project)"
              />
            </div>
          </li>
        </ul>

        <footer class="pager">
          <span>共 {{ pagination.count }} 个项目</span>
          <div v-if="pagination.count > pagination.limit">
            <button
              type="button"
              :disabled="pagination.current <= 1 || loading"
              @click="changePage(pagination.current - 1)"
            >
              上一页
            </button>
            <span>{{ pagination.current }} / {{ totalPages }}</span>
            <button
              type="button"
              :disabled="pagination.current >= totalPages || loading"
              @click="changePage(pagination.current + 1)"
            >
              下一页
            </button>
          </div>
        </footer>
      </template>
      </div>
    </div>

    <DeleteProjectDialog
      v-model="deleteVisible"
      :project="deletingProject"
      @deleted="handleDeleted"
    />
    <RenameProjectDemoDialog
      v-model="renameVisible"
      :project="renamingProject"
      @renamed="handleRenamed"
    />
  </HomeLayout>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue';
import { useRouter } from 'vue-router';
import Message from '@/common/message';
import { fromNowFormatter, readableError, timeFormatter } from '@/common/util';
import AppIcon from '@/components/AppIcon.vue';
import DeleteProjectDialog from '@/components/project/DeleteProjectDialog.vue';
import ProjectActionsMenu from '@/components/project/ProjectActionsMenu.vue';
import RenameProjectDemoDialog from '@/components/project/RenameProjectDemoDialog.vue';
import { listProjects } from '@/http/api';
import type { ProjectResponse } from '@/http/types';
import HomeLayout from '@/layouts/HomeLayout.vue';

const router = useRouter();
const loading = ref(false);
const listError = ref('');
const projects = ref<ProjectResponse[]>([]);
const deleteVisible = ref(false);
const deletingProject = ref<ProjectResponse | null>(null);
const renameVisible = ref(false);
const renamingProject = ref<ProjectResponse | null>(null);
const pagination = reactive({ current: 1, count: 0, limit: 30 });
const totalPages = computed(() => Math.max(1, Math.ceil(pagination.count / pagination.limit)));

const fetchProjects = async () => {
  loading.value = true;
  listError.value = '';
  try {
    const response = await listProjects({
      page: pagination.current,
      page_size: pagination.limit,
    });
    projects.value = response.items || [];
    pagination.count = response.count || 0;
  } catch (error) {
    listError.value = readableError(error, '项目列表加载失败，请稍后重试');
    if (!projects.value.length) pagination.count = 0;
  } finally {
    loading.value = false;
  }
};

const createProject = () => {
  router.push({ name: 'home', query: { compose: '1' } });
};

const enterProject = (project: ProjectResponse) => {
  router.push({ name: 'project', params: { projectId: project.id } });
};

const changePage = (page: number) => {
  pagination.current = page;
  fetchProjects();
};

const openDelete = (project: ProjectResponse) => {
  deletingProject.value = project;
  deleteVisible.value = true;
};

const openRename = (project: ProjectResponse) => {
  renamingProject.value = project;
  renameVisible.value = true;
};

const handleRenamed = (name: string) => {
  if (renamingProject.value) renamingProject.value.name = name;
  Message({
    theme: 'primary',
    message: '演示名称已临时更新，刷新页面后会恢复',
  });
};

const handleDeleted = async () => {
  const id = deletingProject.value?.id;
  if (id) {
    projects.value = projects.value.filter(project => project.id !== id);
    pagination.count = Math.max(0, pagination.count - 1);
  }
  if (!projects.value.length && pagination.current > 1) pagination.current -= 1;
  await fetchProjects();
};

fetchProjects();
</script>

<style lang="postcss" scoped>
.projects-page {
  width: 100%;
  min-height: 100%;
  background: var(--subtle-bg);
}

.projects-page__inner {
  width: min(1080px, 100%);
  margin: 0 auto;
  padding: 32px clamp(20px, 4vw, 48px) 56px;
}

.projects-page__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 20px;
}

.projects-page__head h1 {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 0;
  color: var(--ink);
  font-size: 24px;
  font-weight: 600;
  letter-spacing: -0.02em;
}

.count-chip {
  min-width: 26px;
  height: 22px;
  padding: 0 8px;
  color: var(--muted);
  font-size: 13px;
  font-weight: 500;
  font-variant-numeric: tabular-nums;
  line-height: 22px;
  text-align: center;
  background: var(--hover-bg);
  border-radius: 999px;
}

.projects-page__create {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  min-height: 36px;
  padding: 0 16px 0 12px;
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  background: var(--bk-primary);
  border: 0;
  border-radius: 10px;
}

.projects-page__create:hover {
  background: var(--bk-primary-hover);
}

.projects-page__create :deep(.app-icon) {
  font-size: 16px;
}

.project-rows {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.project-row {
  position: relative;
  display: flex;
  min-height: 60px;
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 14px;
  transition: border-color 150ms ease, box-shadow 150ms ease;
}

.project-row:hover {
  border-color: #c6d2ea;
  box-shadow: 0 6px 18px rgba(18, 28, 48, 0.06);
}

.project-row__open {
  display: grid;
  flex: 1;
  grid-template-columns: minmax(0, 1fr) 180px;
  align-items: center;
  gap: 16px;
  min-width: 0;
  padding: 10px 60px 10px 20px;
  color: inherit;
  text-align: left;
  background: transparent;
  border: 0;
  cursor: pointer;
}

.project-row__main {
  display: flex;
  align-items: baseline;
  gap: 10px;
  min-width: 0;
}

.project-row__main strong {
  overflow: hidden;
  color: var(--ink);
  font-size: 15px;
  font-weight: 600;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.project-row__main code {
  flex-shrink: 0;
  color: var(--faint);
  font-family: var(--font-mono);
  font-size: 12px;
}

.project-row time {
  color: var(--faint);
  font-size: 13px;
  font-variant-numeric: tabular-nums;
  text-align: right;
  white-space: nowrap;
}

.project-row__actions {
  position: absolute;
  top: 50%;
  right: 12px;
  transform: translateY(-50%);
}

.project-row__open:focus-visible,
.projects-page__create:focus-visible {
  outline: 2px solid var(--accent-focus);
  outline-offset: 2px;
}

.skeleton-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 120px 150px;
  align-items: center;
  gap: 16px;
  height: 60px;
  padding: 0 20px;
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 14px;
}

.skeleton-row i {
  height: 12px;
  background: linear-gradient(90deg, #eef1f6 25%, #f7f9fc 37%, #eef1f6 63%);
  background-size: 400% 100%;
  border-radius: 6px;
  animation: skeleton 1.4s ease infinite;
}

.skeleton-row i:first-child {
  width: 40%;
}

.list-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 72px 24px;
  text-align: center;
  background: #fff;
  border: 1px dashed #d5dce8;
  border-radius: 16px;
}

.list-state h2 {
  margin: 0;
  color: var(--ink);
  font-size: 18px;
}

.list-state p {
  margin: 8px 0 20px;
  color: var(--muted);
  font-size: 14px;
}

.inline-error {
  display: flex;
  gap: 12px;
  margin: 0 0 16px;
  color: #8a2b2b;
  font-size: 13px;
}

.inline-error button,
.pager button {
  padding: 0;
  color: var(--accent);
  background: transparent;
  border: 0;
  cursor: pointer;
}

.pager {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-top: 22px;
  color: var(--faint);
  font-size: 13px;
}

.pager div {
  display: flex;
  align-items: center;
  gap: 12px;
}

.pager button:disabled {
  color: #a8b0bd;
  cursor: not-allowed;
}

@keyframes skeleton {
  from { background-position: 100% 50%; }
  to { background-position: 0 50%; }
}

@media (max-width: 760px) {
  .projects-page__inner {
    padding-inline: 16px;
  }

  .projects-page__head {
    align-items: flex-start;
    flex-direction: column;
  }

  .project-row__open {
    grid-template-columns: minmax(0, 1fr);
  }

  .project-row time,
  .project-row__main code {
    display: none;
  }

  .pager {
    align-items: flex-start;
    flex-direction: column;
  }
}

@media (prefers-reduced-motion: reduce) {
  .skeleton-row i {
    animation: none;
  }

  .project-row {
    transition: none;
  }
}
</style>
