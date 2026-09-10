<template>
  <HomeLayout>
    <div class="home-page">
      <section class="hero">
        <h1>{{ greeting }}</h1>
        <p>用自然语言开发可部署的蓝鲸 SaaS。从下一个项目开始。</p>
        <bk-button
          class="hero__cta"
          theme="primary"
          size="large"
          @click="openCreate"
        >
          创建项目
        </bk-button>
      </section>

      <section class="library" aria-live="polite">
        <div class="library__head">
          <h2>我的项目</h2>
          <p v-if="pagination.count">{{ pagination.count }} 个</p>
        </div>

        <bk-loading :loading="loading">
          <div
            v-if="listError && !projects.length"
            class="state-panel"
            role="alert"
          >
            <h3>项目没有加载出来</h3>
            <p>{{ listError }}</p>
            <bk-button theme="primary" @click="fetchProjects">
              重试
            </bk-button>
          </div>

          <div
            v-else-if="!loading && !pagination.count"
            class="state-panel"
          >
            <h3>工作室还是空的</h3>
            <p>创建第一个项目后，就可以在对话里把应用做出来。</p>
            <bk-button
              class="create-project-btn"
              theme="primary"
              @click="openCreate"
            >
              创建项目
            </bk-button>
          </div>

          <div v-else-if="projects.length">
            <p
              v-if="listError"
              class="inline-error"
              role="alert"
            >
              {{ listError }}
              <button type="button" class="text-action" @click="fetchProjects">
                重试
              </button>
            </p>

            <ul class="card-grid">
              <li>
                <button
                  type="button"
                  class="create-card"
                  @click="openCreate"
                >
                  <Plus
                    class="create-card__plus"
                    width="72px"
                    height="72px"
                  />
                  <span class="create-card__title">新项目</span>
                  <span class="create-card__hint">用一句话开始</span>
                </button>
              </li>
              <li
                v-for="row in projects"
                :key="row.id"
              >
                <article
                  class="project-card"
                  role="button"
                  tabindex="0"
                  :aria-label="`进入项目 ${row.name}`"
                  @click="enterProject(row)"
                  @keydown.enter.prevent="enterProject(row)"
                  @keydown.space.prevent="enterProject(row)"
                >
                  <header class="project-card__top">
                    <h3>{{ row.name }}</h3>
                    <p class="project-card__id">{{ row.id }}</p>
                  </header>
                  <footer class="project-card__foot">
                    <time :datetime="row.updated">
                      更新于 {{ timeFormatter(row.updated, 'YYYY-MM-DD HH:mm') }}
                    </time>
                    <span>进入</span>
                  </footer>
                </article>
              </li>
            </ul>

            <div class="pager">
              <p>共 {{ pagination.count }} 个项目</p>
              <div
                v-if="pagination.count > pagination.limit"
                class="pager__nav"
              >
                <button
                  type="button"
                  class="pager__btn"
                  :disabled="pagination.current <= 1 || loading"
                  @click="handlePageChange(pagination.current - 1)"
                >
                  上一页
                </button>
                <span>{{ pagination.current }} / {{ totalPages }}</span>
                <button
                  type="button"
                  class="pager__btn"
                  :disabled="pagination.current >= totalPages || loading"
                  @click="handlePageChange(pagination.current + 1)"
                >
                  下一页
                </button>
              </div>
            </div>
          </div>
        </bk-loading>
      </section>
    </div>

    <CreateProjectDialog
      v-model="dialogVisible"
      @created="enterProject"
    />
  </HomeLayout>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue';
import { useRouter } from 'vue-router';
import { Plus } from 'bkui-vue/lib/icon';
import { listProjects } from '@/http/api';
import type { ProjectResponse } from '@/http/types';
import CreateProjectDialog from '@/components/project/CreateProjectDialog.vue';
import HomeLayout from '@/layouts/HomeLayout.vue';
import { timeFormatter } from '@/common/util';
import { useUser } from '@/store/user';

const router = useRouter();
const user = useUser();
const loading = ref(false);
const dialogVisible = ref(false);
const listError = ref('');
const projects = ref<ProjectResponse[]>([]);

const greeting = computed(() => {
  const name = user.user.display_name || user.user.username;
  return name ? `你好，${name}` : '开始下一个蓝鲸 SaaS';
});

const pagination = reactive({
  current: 1,
  count: 0,
  limit: 11,
});

const totalPages = computed(() => (
  Math.max(1, Math.ceil(pagination.count / pagination.limit))
));

const enterProject = (row: ProjectResponse) => {
  router.push({ name: 'project', params: { projectId: row.id } });
};

const handlePageChange = (page: number) => {
  pagination.current = page;
  fetchProjects();
};

const openCreate = () => {
  dialogVisible.value = true;
};

const fetchProjects = async () => {
  loading.value = true;
  listError.value = '';
  try {
    const data = await listProjects({
      page: pagination.current,
      page_size: pagination.limit,
    });
    projects.value = data.items || [];
    pagination.count = data.count || 0;
  } catch (error: any) {
    listError.value = error?.message || '项目列表加载失败，请稍后重试';
    if (!projects.value.length) {
      pagination.count = 0;
    }
  } finally {
    loading.value = false;
  }
};

fetchProjects();
</script>

<style lang="postcss" scoped>
.home-page {
  --ink: #12151c;
  --muted: #556070;
  --faint: #7a8494;
  --paper: #ffffff;
  --line: #dbe3ee;
  --accent: #2f5bff;
  --focus: #1f46d6;
  width: 100%;
  color: var(--ink);
}

.home-page ::selection {
  background: #d7e0ff;
  color: var(--ink);
}

.hero {
  max-width: 34em;
  padding: 28px 0 48px;
}

.hero h1 {
  margin: 0 0 14px;
  font-size: clamp(40px, 6vw, 64px);
  font-weight: 600;
  letter-spacing: -0.045em;
  line-height: 1.05;
}

.hero p {
  margin: 0 0 28px;
  color: var(--muted);
  font-size: 18px;
  line-height: 1.55;
}

.hero :deep(.hero__cta),
:deep(.create-project-btn) {
  --bk-button-primary-hover-bg: #1768ef;
  background: #3a84ff !important;
  border-color: #3a84ff !important;
}

.hero :deep(.hero__cta) {
  min-width: 148px;
  height: 44px;
}

.library__head {
  display: flex;
  align-items: baseline;
  gap: 12px;
  margin-bottom: 18px;
}

.library__head h2 {
  margin: 0;
  font-size: 22px;
  font-weight: 600;
  letter-spacing: -0.03em;
}

.library__head p {
  margin: 0;
  color: var(--faint);
  font-size: 14px;
}

.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(min(100%, 260px), 1fr));
  gap: 18px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.project-card,
.create-card {
  display: flex;
  flex-direction: column;
  width: 100%;
  min-height: 220px;
  padding: 22px 22px 18px;
  text-align: left;
  background: var(--paper);
  border: 1px solid var(--line);
  border-radius: 18px;
  box-shadow: 0 12px 28px rgba(18, 28, 48, 0.06);
  cursor: pointer;
}

.project-card {
  justify-content: space-between;
  transition: transform 180ms cubic-bezier(0.16, 1, 0.3, 1), box-shadow 180ms ease;
}

.project-card:hover,
.create-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 18px 36px rgba(18, 28, 48, 0.1);
}

.project-card:focus,
.create-card:focus {
  outline: none;
}

.project-card:focus-visible,
.create-card:focus-visible {
  outline: 2px solid var(--focus);
  outline-offset: 3px;
}

.project-card h3 {
  margin: 0 0 10px;
  overflow: hidden;
  font-size: 22px;
  font-weight: 600;
  letter-spacing: -0.03em;
  line-height: 1.25;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.project-card__id {
  margin: 0;
  color: var(--faint);
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 12px;
}

.project-card__foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding-top: 16px;
  color: var(--faint);
  font-size: 13px;
  border-top: 1px solid var(--line);
}

.project-card__foot span {
  color: #7b91ff;
  font-weight: 500;
}

.create-card {
  position: relative;
  align-items: flex-start;
  justify-content: flex-end;
  color: inherit;
  background:
    linear-gradient(180deg, rgba(47, 91, 255, 0.07), transparent 46%),
    var(--paper);
}

.create-card__plus {
  position: absolute;
  top: 46%;
  left: 50%;
  color: #8aa0ff;
  font-size: 72px;
  line-height: 1;
  transform: translate(-50%, -50%);
}

.create-card__plus :deep(svg) {
  width: 72px !important;
  height: 72px !important;
}

.create-card__title {
  font-size: 22px;
  font-weight: 600;
  letter-spacing: -0.03em;
}

.create-card__hint {
  margin-top: 6px;
  color: var(--muted);
  font-size: 14px;
}

.state-panel {
  max-width: 28em;
  padding: 28px 0 48px;
}

.state-panel h3 {
  margin: 0 0 8px;
  font-size: 24px;
  font-weight: 600;
  letter-spacing: -0.03em;
}

.state-panel p {
  margin: 0 0 20px;
  color: var(--muted);
  font-size: 15px;
  line-height: 1.6;
}

.inline-error {
  display: flex;
  gap: 12px;
  margin: 0 0 16px;
  color: #8a2b2b;
  font-size: 13px;
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

.pager p {
  margin: 0;
}

.pager__nav {
  display: flex;
  align-items: center;
  gap: 12px;
}

.pager__btn,
.text-action {
  padding: 0;
  color: var(--accent);
  font-size: 13px;
  background: none;
  border: none;
  cursor: pointer;
}

.pager__btn:disabled {
  color: #a8b0bd;
  cursor: not-allowed;
}

.pager__btn:focus-visible,
.text-action:focus-visible {
  outline: 2px solid var(--focus);
  outline-offset: 3px;
}

@media (max-width: 640px) {
  .hero {
    padding-top: 12px;
  }

  .hero p {
    font-size: 16px;
  }

  .pager {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
