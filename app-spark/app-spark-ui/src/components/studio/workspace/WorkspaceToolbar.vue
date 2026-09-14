<template>
  <div class="workspace-toolbar">
    <bk-radio-group v-model="viewType" type="capsule" size="small" @change="emitView">
      <bk-radio-button label="preview">预览</bk-radio-button>
      <bk-radio-button label="code">
        <Code class="workspace-toolbar__icon" />
        代码
      </bk-radio-button>
    </bk-radio-group>

    <bk-radio-group v-model="deviceType" type="capsule" size="small" @change="emitDevice">
      <bk-radio-button label="mobile">手机</bk-radio-button>
      <bk-radio-button label="desktop">桌面</bk-radio-button>
    </bk-radio-group>

    <span class="workspace-toolbar__hint">
      {{ deviceType === 'desktop' ? '桌面端预览' : '移动端预览' }} · template 热更新
    </span>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue';
import { Code } from 'bkui-vue/lib/icon';
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

const emitView = (value: WorkspaceView) => {
  emit('update:view', value);
};

const emitDevice = (value: WorkspaceDevice) => {
  emit('update:device', value);
};
</script>

<style lang="postcss" scoped>
.workspace-toolbar {
  display: flex;
  align-items: center;
  gap: 16px;
  height: 48px;
  padding: 0 16px;
  background: #f5f7fa;
  border-bottom: 1px solid #dcdee5;
}

.workspace-toolbar__icon {
  margin-right: 4px;
}

.workspace-toolbar__hint {
  margin-left: auto;
  color: #979ba5;
  font-size: 12px;
}
</style>
