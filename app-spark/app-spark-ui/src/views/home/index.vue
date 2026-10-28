<template>
  <HomeLayout>
    <div class="home-body">
      <section class="hero">
        <h1>
          把每个灵感变为精彩应用
          <span class="hero__sparks" aria-hidden="true"><i /><i /><i /></span>
        </h1>
        <p>通过和 AI 聊天来创建网站应用</p>

        <form
          ref="composerRef"
          :class="['composer', {
            'is-error': Boolean(createError),
            'is-spotlight': spotlighted,
          }]"
          novalidate
          @submit.prevent="submitPrompt"
          @animationend="handleSpotlightEnd"
        >
          <textarea
            ref="inputRef"
            v-model="prompt"
            class="composer__input"
            rows="3"
            maxlength="2000"
            aria-label="描述你想做的应用"
            placeholder="我想要实现一个…"
            :disabled="creating"
            @input="handleInput"
            @keydown.enter="handleEnter"
          />
          <div class="composer__bar">
            <button
              type="button"
              class="composer__tool"
              aria-label="添加附件"
              aria-disabled="true"
              v-bk-tooltips="'暂不支持添加附件'"
            >
              <AppIcon name="plus-line" />
            </button>
            <ModelSelector />
            <button
              type="submit"
              class="composer__send"
              :disabled="creating || !prompt.trim()"
              :aria-label="creating ? '正在创建项目' : '发送'"
            >
              <span v-if="creating" class="composer__spinner" aria-hidden="true" />
              <AppIcon v-else name="arrow-up" />
            </button>
          </div>
        </form>
        <p v-if="createError" class="composer__error" role="alert">{{ createError }}</p>

        <div class="composer__samples" aria-label="试试这些想法">
          <span>试试：</span>
          <button
            v-for="sample in samples"
            :key="sample.label"
            type="button"
            :disabled="creating"
            @click="applySample(sample.prompt)"
          >
            {{ sample.label }}
          </button>
        </div>
      </section>

      <section class="recent" aria-labelledby="recent-title">
        <header class="recent__head">
          <h2 id="recent-title">最近编辑</h2>
          <router-link class="recent__more" :to="{ name: 'projects' }">
            全部项目
            <AppIcon name="chevron-right" />
          </router-link>
        </header>

        <div v-if="loading" class="recent__grid" aria-busy="true">
          <div v-for="index in 3" :key="index" class="skeleton-card" />
        </div>
        <div v-else-if="listError" class="recent__state is-error" role="alert">
          <p>{{ listError }}</p>
          <button type="button" @click="fetchRecent">重试</button>
        </div>
        <div v-else-if="!projects.length" class="recent__state">
          <p>还没有项目。在上面描述你的想法，AI 会帮你把它做出来。</p>
        </div>
        <ul v-else class="recent__grid">
          <li v-for="project in projects" :key="project.id">
            <article class="recent-card">
              <button
                type="button"
                class="recent-card__open"
                :aria-label="`进入项目 ${project.name}`"
                @click="enterProject(project)"
              >
                <h3 :title="project.name">{{ project.name }}</h3>
                <time :datetime="project.updated_at">
                  更新于 {{ timeFormatter(project.updated_at, 'YYYY-MM-DD HH:mm') }}
                </time>
              </button>
              <div class="recent-card__actions">
                <ProjectActionsMenu
                  placement="top-end"
                  @rename="openRename(project)"
                  @delete="openDelete(project)"
                />
              </div>
            </article>
          </li>
        </ul>
      </section>
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
import { nextTick, onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { generateProjectId, projectNameFromPrompt } from '@/common/project';
import { readableError, timeFormatter } from '@/common/util';
import AppIcon from '@/components/AppIcon.vue';
import ModelSelector from '@/components/model/ModelSelector.vue';
import DeleteProjectDialog from '@/components/project/DeleteProjectDialog.vue';
import ProjectActionsMenu from '@/components/project/ProjectActionsMenu.vue';
import RenameProjectDemoDialog from '@/components/project/RenameProjectDemoDialog.vue';
import { createProject, listProjects } from '@/http/api';
import type { ProjectResponse } from '@/http/types';
import HomeLayout from '@/layouts/HomeLayout.vue';
import { useModelCatalogStore } from '@/store/model-catalog';
import { useProjectStore } from '@/store/project';

const router = useRouter();
const route = useRoute();
const projectStore = useProjectStore();
const modelCatalogStore = useModelCatalogStore();
const composerRef = ref<HTMLFormElement>();
const inputRef = ref<HTMLTextAreaElement>();
const prompt = ref('');
const creating = ref(false);
const createError = ref('');
const loading = ref(false);
const listError = ref('');
const projects = ref<ProjectResponse[]>([]);
const deleteVisible = ref(false);
const deletingProject = ref<ProjectResponse | null>(null);
const renameVisible = ref(false);
const renamingProject = ref<ProjectResponse | null>(null);
const spotlighted = ref(false);

const samples = [
  { label: '番茄钟小工具', prompt: '开发一个番茄钟小工具，使用活泼的配色风格' },
  { label: '活动报名页', prompt: '做一个团队活动报名页，可以填写姓名和人数，并导出名单' },
  { label: '抽奖小工具', prompt: '开发一个抽奖小工具，可录入抽奖名单，奖品固定为一台 Switch 2' },
];

const resizeInput = () => {
  const input = inputRef.value;
  if (!input) return;
  input.style.height = 'auto';
  input.style.height = `${Math.min(Math.max(input.scrollHeight, 72), 240)}px`;
};

const handleInput = () => {
  createError.value = '';
  resizeInput();
};

const handleEnter = (event: KeyboardEvent) => {
  if (event.shiftKey || event.isComposing || event.keyCode === 229) return;
  event.preventDefault();
  submitPrompt();
};

const applySample = async (value: string) => {
  prompt.value = value;
  await nextTick();
  resizeInput();
  inputRef.value?.focus();
};

const submitPrompt = async () => {
  const content = prompt.value.trim();
  if (!content || creating.value) return;
  createError.value = '';
  creating.value = true;
  try {
    const created = await createProject({
      id: generateProjectId(),
      name: projectNameFromPrompt(content),
    });
    projectStore.queueInitialMessage(
      created.id,
      content,
      modelCatalogStore.requestModelCode,
    );
    await router.push({ name: 'project', params: { projectId: created.id } });
  } catch (error) {
    createError.value = readableError(error, '创建失败，请稍后重试');
    creating.value = false;
    await nextTick();
    inputRef.value?.focus();
  }
};

const fetchRecent = async () => {
  loading.value = true;
  listError.value = '';
  try {
    const response = await listProjects({ page: 1, page_size: 3 });
    projects.value = response.items || [];
  } catch (error) {
    listError.value = readableError(error, '项目列表加载失败，请稍后重试');
  } finally {
    loading.value = false;
  }
};

const enterProject = (project: ProjectResponse) => {
  router.push({ name: 'project', params: { projectId: project.id } });
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
};

const handleDeleted = () => {
  fetchRecent();
};

const handleSpotlightEnd = (event: AnimationEvent) => {
  if (event.animationName === 'composer-spin') {
    spotlighted.value = false;
  }
};

fetchRecent();
void modelCatalogStore.loadCatalog();

onMounted(async () => {
  if (route.query.compose !== '1') return;
  inputRef.value?.focus();
  spotlighted.value = false;
  await nextTick();
  void composerRef.value?.offsetWidth;
  spotlighted.value = true;
  router.replace({ name: 'home' });
});
</script>

<style lang="postcss" scoped>
.home-body {
  display: flex;
  flex-direction: column;
  min-height: 100%;
  padding: 0 clamp(20px, 4vw, 56px) 40px;
  color: var(--ink);
  background-color: #d9e3f2;
  background-image:
    radial-gradient(ellipse 72% 52% at 6% -4%, rgba(91, 132, 255, 0.5), transparent 56%),
    radial-gradient(ellipse 50% 40% at 96% 4%, rgba(56, 189, 248, 0.32), transparent 52%),
    radial-gradient(ellipse 58% 46% at 78% 108%, rgba(129, 140, 248, 0.28), transparent 58%),
    linear-gradient(168deg, #f3f6ff 0%, #dbe6f8 38%, #e3eef7 68%, #d5ebe6 100%);
  background-attachment: fixed;
}

.hero {
  display: flex;
  flex: 1;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 470px;
  padding: 56px 0 32px;
  text-align: center;
}

.hero h1 {
  position: relative;
  margin: 0;
  font-size: clamp(30px, 4.2vw, 44px);
  font-weight: 700;
  letter-spacing: -0.03em;
  line-height: 1.15;
}

.hero h1 + p {
  margin: 12px 0 0;
  color: var(--muted);
  font-size: 16px;
}

.hero__sparks {
  position: absolute;
  top: -0.35em;
  left: 100%;
  width: 0.95em;
  height: 1em;
  margin-left: 0.12em;
  filter: drop-shadow(0 0 6px rgba(255, 95, 143, 0.45));
  pointer-events: none;
}

.hero__sparks i {
  position: absolute;
  display: block;
  background: var(--spark-gradient);
  clip-path: var(--spark-shape);
}

.hero__sparks i:nth-child(1) {
  top: 0.18em;
  left: 0.12em;
  width: 0.56em;
  height: 0.56em;
  animation: hero-spark-pop 3.2s ease-in-out infinite;
}

.hero__sparks i:nth-child(2) {
  top: 0;
  left: 0.64em;
  width: 0.24em;
  height: 0.24em;
  animation: hero-spark-twinkle 2.4s ease-in-out 0.4s infinite;
}

.hero__sparks i:nth-child(3) {
  top: 0.7em;
  left: 0.68em;
  width: 0.16em;
  height: 0.16em;
  animation: hero-spark-twinkle 2s ease-in-out 1.1s infinite;
}

@property --composer-angle {
  syntax: "<angle>";
  inherits: false;
  initial-value: 0deg;
}

.composer {
  position: relative;
  width: 100%;
  max-width: 720px;
  margin-top: 32px;
  padding: 16px 14px 12px 18px;
  text-align: left;
  background: #fff;
  border: 1px solid #d5ddea;
  border-radius: 20px;
  box-shadow: 0 12px 32px rgba(18, 28, 48, 0.08);
  transition: border-color 160ms ease, box-shadow 160ms ease;
}

.composer:focus-within {
  border-color: #a9b9ff;
  box-shadow: 0 0 0 4px rgba(61, 109, 255, 0.12), 0 12px 32px rgba(18, 28, 48, 0.08);
}

.composer.is-error {
  border-color: #e76761;
}

.composer::before {
  position: absolute;
  inset: -2px;
  padding: 2px;
  pointer-events: none;
  content: "";
  background: conic-gradient(
    from var(--composer-angle),
    transparent 0deg,
    transparent 220deg,
    #7c5cff 300deg,
    #3d6dff 345deg,
    transparent 360deg
  );
  border-radius: 22px;
  opacity: 0;
  -webkit-mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0);
  -webkit-mask-composite: xor;
  mask: linear-gradient(#000 0 0) content-box exclude, linear-gradient(#000 0 0);
}

.composer.is-spotlight::before {
  animation: composer-spin 1.4s cubic-bezier(0.4, 0, 0.2, 1) forwards;
}

.composer__input {
  display: block;
  width: 100%;
  min-height: 72px;
  max-height: 240px;
  padding: 0;
  overflow-y: auto;
  color: var(--ink);
  font-size: 16px;
  line-height: 24px;
  resize: none;
  background: transparent;
  border: 0;
  outline: none;
}

.composer__input::placeholder {
  color: #707b8c;
}

.composer__bar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
}

.composer__tool,
.composer__send {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: 0;
}

.composer__tool {
  height: 32px;
  color: var(--muted);
  cursor: not-allowed;
  border-radius: 10px;
  opacity: 0.5;
}

.composer__tool {
  width: 32px;
  padding: 0;
  border: 1px solid var(--line);
}

.composer__tool :deep(.app-icon) {
  font-size: 16px;
}

.composer__send :deep(.app-icon),
.recent-card__actions :deep(.app-icon) {
  font-size: 18px;
}

.composer__send {
  width: 36px;
  height: 36px;
  margin-left: auto;
  color: #fff;
  cursor: pointer;
  background: var(--accent);
  border-radius: 12px;
}

.composer__send:hover:not(:disabled) {
  background: #274edb;
}

.composer__send:disabled {
  cursor: not-allowed;
  background: #c9d3e6;
}

.composer__spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.45);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.composer__error {
  margin: 12px 0 0;
  color: #b42318;
  font-size: 13px;
}

.composer__samples {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-top: 16px;
  color: var(--faint);
  font-size: 13px;
}

.composer__samples button {
  height: 30px;
  padding: 0 12px;
  color: var(--muted);
  font-size: 13px;
  cursor: pointer;
  background: rgba(255, 255, 255, 0.78);
  border: 1px solid rgba(255, 255, 255, 0.95);
  border-radius: 999px;
}

.composer__samples button:hover:not(:disabled) {
  color: var(--ink);
  background: #fff;
}

.composer__samples button:focus-visible,
.composer__send:focus-visible,
.composer__tool:focus-visible {
  outline: 2px solid var(--accent-focus);
  outline-offset: 2px;
}

.recent {
  width: 100%;
  max-width: 1080px;
  margin: 0 auto;
  padding: 18px 20px 20px;
  background: rgba(255, 255, 255, 0.82);
  border: 1px solid rgba(255, 255, 255, 0.92);
  border-radius: 20px;
  box-shadow: 0 12px 32px rgba(18, 28, 48, 0.06);
  backdrop-filter: blur(12px);
}

.recent__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}

.recent__head h2 {
  margin: 0;
  padding-bottom: 6px;
  color: var(--accent);
  font-size: 14px;
  font-weight: 600;
  border-bottom: 2px solid var(--accent);
}

.recent__more {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  color: var(--accent);
  font-size: 13px;
  text-decoration: none;
}

.recent__more :deep(.app-icon) {
  font-size: 14px;
}

.recent__more:hover {
  text-decoration: underline;
  text-underline-offset: 3px;
}

.recent__grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.recent-card {
  position: relative;
  min-height: 108px;
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 14px;
  transition: transform 180ms ease, box-shadow 180ms ease, border-color 180ms ease;
}

.recent-card:hover {
  border-color: #c6d2ea;
  box-shadow: 0 12px 24px rgba(18, 28, 48, 0.08);
  transform: translateY(-2px);
}

.recent-card__open {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  width: 100%;
  min-height: 106px;
  padding: 16px 46px 16px 18px;
  color: inherit;
  text-align: left;
  background: transparent;
  border: 0;
  cursor: pointer;
}

.recent-card h3 {
  margin: 0;
  overflow: hidden;
  color: var(--ink);
  font-size: 15px;
  font-weight: 600;
  line-height: 24px;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.recent-card time {
  margin-top: 16px;
  color: var(--faint);
  font-size: 13px;
}

.recent-card__actions {
  position: absolute;
  right: 8px;
  bottom: 8px;
}

.recent-card__open:focus-visible {
  outline: 2px solid var(--accent-focus);
  outline-offset: 2px;
}

.skeleton-card {
  height: 108px;
  background: linear-gradient(90deg, #eef1f6 25%, #f7f9fc 37%, #eef1f6 63%);
  background-size: 400% 100%;
  border-radius: 14px;
  animation: skeleton 1.4s ease infinite;
}

.recent__state {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  min-height: 108px;
  color: var(--muted);
  font-size: 14px;
}

.recent__state p {
  margin: 0;
}

.recent__state.is-error p {
  color: #8a2b2b;
}

.recent__state button {
  padding: 0;
  color: var(--accent);
  background: transparent;
  border: 0;
  cursor: pointer;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@keyframes composer-spin {
  0% {
    --composer-angle: 0deg;
    opacity: 0;
  }

  12%,
  80% {
    opacity: 1;
  }

  100% {
    --composer-angle: 360deg;
    opacity: 0;
  }
}

@keyframes skeleton {
  from { background-position: 100% 50%; }
  to { background-position: 0 50%; }
}

@keyframes hero-spark-pop {
  0%,
  70%,
  100% { transform: rotate(0) scale(1); }
  82% { transform: rotate(90deg) scale(1.12); }
}

@keyframes hero-spark-twinkle {
  0%,
  100% { opacity: 0.35; transform: scale(0.7); }
  50% { opacity: 1; transform: scale(1); }
}

@media (max-width: 760px) {
  .home-body {
    padding-inline: 16px;
  }

  .hero {
    min-height: 430px;
    padding-top: 36px;
  }

  .hero__sparks {
    display: none;
  }

  .recent__grid {
    grid-template-columns: minmax(0, 1fr);
  }
}

@media (prefers-reduced-motion: reduce) {
  .hero__sparks i,
  .composer__spinner,
  .skeleton-card {
    animation: none;
  }

  .composer.is-spotlight::before {
    animation-duration: 0.01s;
  }

  .recent-card,
  .composer {
    transition: none;
  }
}
</style>
