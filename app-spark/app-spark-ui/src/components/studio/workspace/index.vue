<template>
  <section class="workspace-panel">
    <WorkspaceToolbar v-model:view="view" v-model:device="device" />
    <PreviewCanvas
      v-if="view === 'preview'"
      :device="device"
      :src="previewUrl"
      :busy="busy"
    />
    <div v-else class="workspace-panel__code">
      代码在 template 工程中。左侧提需求后，Agent 会改这里，预览热更新。
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { storeToRefs } from 'pinia';
import { useStudioStore } from '@/store/studio';
import PreviewCanvas from './PreviewCanvas.vue';
import WorkspaceToolbar from './WorkspaceToolbar.vue';
import type { WorkspaceDevice, WorkspaceView } from './types';

const previewUrl = process.env.BK_TEMPLATE_URL || (process.env.NODE_ENV === 'development'
  ? process.env.BK_TEMPLATE_DEV_URL || 'http://localhost:5173'
  : 'about:blank');
const view = ref<WorkspaceView>('preview');
const device = ref<WorkspaceDevice>('desktop');
const { busy } = storeToRefs(useStudioStore());
</script>

<style lang="postcss" scoped>
.workspace-panel {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-width: 0;
}

.workspace-panel__code {
  display: flex;
  flex: 1;
  align-items: center;
  justify-content: center;
  padding: 24px;
  color: #979ba5;
  background: #1e1e1e;
}
</style>
