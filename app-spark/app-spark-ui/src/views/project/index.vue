<template>
  <bk-loading
    class="project-page-loading"
    :loading="entering"
    :opacity="0.96"
    :z-index="20"
    color="#f3f5f8"
  >
    <ProjectLayout>
      <InteractionPanel />
      <WorkspacePanel />
      <ManagementPanel />
    </ProjectLayout>
  </bk-loading>
</template>

<script setup lang="ts">
import { onUnmounted, watch } from 'vue';
import { useRoute } from 'vue-router';
import { storeToRefs } from 'pinia';
import { Message } from 'bkui-vue';
import InteractionPanel from '@/components/project/interaction/index.vue';
import ManagementPanel from '@/components/project/management/index.vue';
import WorkspacePanel from '@/components/project/workspace/index.vue';
import ProjectLayout from '@/layouts/ProjectLayout.vue';
import { useProjectStore } from '@/store/project';

const route = useRoute();
const projectStore = useProjectStore();
const { entering } = storeToRefs(projectStore);

watch(() => route.params.projectId, async (projectId) => {
  const id = String(projectId || '');
  if (!id) return;
  try {
    await projectStore.enterProject(id);
  } catch (error) {
    Message({
      theme: 'error',
      message: error instanceof Error ? error.message : '进入项目失败',
    });
  }
}, { immediate: true });

onUnmounted(() => {
  projectStore.reset();
});
</script>

<style lang="postcss" scoped>
.project-page-loading {
  height: 100%;
}

.project-page-loading :deep(.bk-loading-mask) {
  z-index: 20;
}

.project-page-loading :deep(.bk-loading-indicator) {
  z-index: 21;
}
</style>
