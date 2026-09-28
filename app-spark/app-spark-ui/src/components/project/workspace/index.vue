<template>
  <section class="workspace-panel">
    <WorkspaceToolbar v-model:view="view" v-model:device="device" />
    <PreviewCanvas
      v-if="view === 'preview'"
      :device="device"
      :src="frameSrc"
      :phase="phase"
      :waiting="waiting"
      :busy="busy"
    />
    <div v-else class="workspace-panel__code">
      敬请期待
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import { storeToRefs } from 'pinia';
import { useConversationPreview } from '@/composables/use-conversation-preview';
import { useProjectStore } from '@/store/project';
import PreviewCanvas from './PreviewCanvas.vue';
import WorkspaceToolbar from './WorkspaceToolbar.vue';
import type { WorkspaceDevice, WorkspaceView } from './types.js';

const view = ref<WorkspaceView>('preview');
const device = ref<WorkspaceDevice>('desktop');
const { busy } = storeToRefs(useProjectStore());
const panelOpen = computed(() => view.value === 'preview');
const { phase, frameSrc, waiting } = useConversationPreview(panelOpen);
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
  color: var(--faint, #88919e);
  background: #15171c;
}
</style>
