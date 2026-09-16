<template>
  <div class="workspace-toolbar">
    <div class="seg" role="tablist" aria-label="视图">
      <button
        type="button"
        role="tab"
        :class="{ 'is-on': viewType === 'preview' }"
        :aria-selected="viewType === 'preview'"
        @click="setView('preview')"
      >
        预览
      </button>
      <button
        type="button"
        role="tab"
        :class="{ 'is-on': viewType === 'code' }"
        :aria-selected="viewType === 'code'"
        @click="setView('code')"
      >
        代码
      </button>
    </div>

    <div
      v-if="viewType === 'preview'"
      class="seg"
      role="tablist"
      aria-label="设备"
    >
      <button
        type="button"
        role="tab"
        :class="{ 'is-on': deviceType === 'mobile' }"
        :aria-selected="deviceType === 'mobile'"
        @click="setDevice('mobile')"
      >
        手机
      </button>
      <button
        type="button"
        role="tab"
        :class="{ 'is-on': deviceType === 'desktop' }"
        :aria-selected="deviceType === 'desktop'"
        @click="setDevice('desktop')"
      >
        Web
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue';
import type { WorkspaceDevice, WorkspaceView } from './types';

const props = withDefaults(defineProps<{
  view?: WorkspaceView;
  device?: WorkspaceDevice;
}>(), {
  view: 'preview',
  device: 'desktop',
});

const emit = defineEmits<{
  (e: 'update:view', value: WorkspaceView): void;
  (e: 'update:device', value: WorkspaceDevice): void;
}>();

const viewType = ref<WorkspaceView>(props.view);
const deviceType = ref<WorkspaceDevice>(props.device);

watch(() => props.view, (value) => {
  viewType.value = value;
});

watch(() => props.device, (value) => {
  deviceType.value = value;
});

const setView = (value: WorkspaceView) => {
  viewType.value = value;
  emit('update:view', value);
};

const setDevice = (value: WorkspaceDevice) => {
  deviceType.value = value;
  emit('update:device', value);
};
</script>

<style lang="postcss" scoped>
.workspace-toolbar {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  gap: 10px;
  height: var(--rail-h, 56px);
  padding: 0 16px;
  background: #fff;
  border-bottom: 1px solid var(--line, #e4e9f1);
}

.seg {
  display: inline-flex;
  padding: 3px;
  background: #f3f4f7;
  border-radius: 10px;
}

.seg button {
  height: 28px;
  padding: 0 12px;
  color: var(--muted, #5c6573);
  font-size: 13px;
  background: transparent;
  border: 0;
  border-radius: 8px;
  cursor: pointer;
}

.seg button.is-on {
  color: var(--ink, #12141a);
  font-weight: 600;
  background: #fff;
  box-shadow: 0 1px 3px rgba(18, 28, 48, 0.08);
}

.seg button:focus-visible {
  outline: 2px solid var(--accent, #3d6dff);
  outline-offset: 2px;
}
</style>
