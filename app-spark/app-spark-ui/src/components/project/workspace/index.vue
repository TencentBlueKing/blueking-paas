<template>
  <section class="workspace-panel">
    <WorkspaceToolbar />
    <PreviewCanvas
      v-model:device="device"
      :src="frameSrc"
      :frame-key="frameKey + manualRefreshKey"
      :phase="phase"
      :waiting="waiting"
      :busy="busy"
      @refresh="manualRefreshKey += 1"
    />
  </section>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import { storeToRefs } from 'pinia';
import { useConversationPreview } from '@/composables/use-conversation-preview';
import { useProjectStore } from '@/store/project';
import PreviewCanvas from './PreviewCanvas.vue';
import WorkspaceToolbar from './WorkspaceToolbar.vue';
import type { WorkspaceDevice } from './types.js';

const device = ref<WorkspaceDevice>('desktop');
const manualRefreshKey = ref(0);
const { busy } = storeToRefs(useProjectStore());
const panelOpen = computed(() => true);
const { phase, frameSrc, frameKey, waiting } = useConversationPreview(panelOpen);
</script>

<style lang="postcss" scoped>
.workspace-panel {
  display: flex;
  flex: 1;
  flex-direction: column;
  height: 100%;
  min-width: 0;
  min-height: 0;
}
</style>
