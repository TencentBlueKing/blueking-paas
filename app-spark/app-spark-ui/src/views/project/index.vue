<template>
  <bk-loading
    class="project-page-loading"
    :loading="entering"
    :opacity="0.96"
    :z-index="20"
    color="#f3f5f8"
  >
    <ProjectLayout>
      <ResizeLayout
        class="project-resize-layout"
        placement="left"
        :initial-divide="400"
        :min="280"
        :max="1000"
        :border="false"
        immediate
        collapsible
      >
        <template #aside>
          <InteractionPanel />
        </template>
        <template #main>
          <WorkspacePanel />
        </template>
      </ResizeLayout>
    </ProjectLayout>
  </bk-loading>
</template>

<script setup lang="ts">
import { onUnmounted, watch } from 'vue';
import { ResizeLayout } from 'bkui-vue';
import { useRoute } from 'vue-router';
import { storeToRefs } from 'pinia';
import Message from '@/common/message';
import InteractionPanel from '@/components/project/interaction/index.vue';
import WorkspacePanel from '@/components/project/workspace/index.vue';
import ProjectLayout from '@/layouts/ProjectLayout.vue';
import { useModelCatalogStore } from '@/store/model-catalog';
import { useProjectStore } from '@/store/project';

const route = useRoute();
const projectStore = useProjectStore();
const modelCatalogStore = useModelCatalogStore();
const { entering } = storeToRefs(projectStore);

watch(() => route.params.projectId, async (projectId) => {
  const id = String(projectId || '');
  if (!id) return;
  try {
    await Promise.all([
      projectStore.enterProject(id),
      modelCatalogStore.loadCatalog(),
    ]);
    if (String(route.params.projectId || '') !== id) return;
    const initialMessage = projectStore.consumeInitialMessage(id);
    if (initialMessage) {
      await projectStore.sendMessage(
        initialMessage.content,
        [],
        initialMessage.modelId,
      );
    }
  } catch (error) {
    projectStore.consumeInitialMessage(id);
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

.project-resize-layout {
  width: 100%;
  height: 100%;
  min-width: 0;
  min-height: 0;
}
</style>
