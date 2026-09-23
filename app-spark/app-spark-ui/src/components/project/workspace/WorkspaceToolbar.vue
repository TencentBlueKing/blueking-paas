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

    <!--
      直接当链接用，而不是 fetch 下来再造 blob：压缩包多大取决于项目源码，交给浏览器原生下载既
      不占内存，也能沿用它自带的下载进度。文件名由响应头给出（带 commit 短 SHA）。
      target="_blank" 是留给出错的那一下：后端报错时返回的是 JSON，让它显示在新标签里，而不是
      把用户从对话页面上带走。
    -->
    <a
      v-if="archiveUrl"
      class="workspace-toolbar__download"
      :href="archiveUrl"
      target="_blank"
      rel="noopener"
      v-bk-tooltips="{
        content: '下载主分支源码，不含本轮尚未保存的改动',
        placement: 'bottom-end',
      }"
    >
      下载源码
    </a>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue';
import { storeToRefs } from 'pinia';
import { useSourceArchive } from '@/composables/use-source-archive';
import { useProjectStore } from '@/store/project';
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

const { projectId } = storeToRefs(useProjectStore());
const { archiveUrl } = useSourceArchive(projectId);

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

/* margin-left: auto 把它推到最右：左边的设备切换只在预览视图下存在，靠它才能不受影响地贴边。 */
.workspace-toolbar__download {
  margin-left: auto;
  color: var(--accent, #3d6dff);
  font-size: 13px;
  text-decoration: none;
  white-space: nowrap;
}

.workspace-toolbar__download:hover {
  text-decoration: underline;
}

.workspace-toolbar__download:focus-visible {
  outline: 2px solid var(--accent, #3d6dff);
  outline-offset: 2px;
  border-radius: 4px;
}
</style>
