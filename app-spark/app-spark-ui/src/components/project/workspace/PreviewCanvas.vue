<template>
  <div class="preview-canvas">
    <div
      :class="['preview-frame', `preview-frame--${device}`, { 'is-busy': busy || waiting }]"
    >
      <div
        class="preview-frame__marquee"
        :class="{ 'is-active': busy || waiting }"
        aria-hidden="true"
      >
        <span class="preview-frame__marquee-bar" />
      </div>
      <div class="preview-frame__body">
        <!--
          src 就是 preview 接口的 origin，末尾带斜杠。后面的路径由页面自己跳。
          非 ready 时 src 为空，iframe 不挂，502 / 503 不会留在这里。
        -->
        <iframe
          v-if="src"
          class="preview-frame__iframe"
          title="应用预览"
          :src="src"
        />
        <div
          v-else
          class="preview-frame__empty"
          role="status"
        >
          {{ placeholder }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { PreviewPhase, WorkspaceDevice } from './types';

const PLACEHOLDER: Record<PreviewPhase, string> = {
  'no-conversation': '正在准备会话…',
  ended: '会话已结束',
  pending: '正在获取预览…',
  unavailable: '预览环境未就绪',
  not_started: '应用尚未启动',
  starting: '应用正在启动…',
  stopped: '应用未在运行',
  ready: '正在打开预览…',
};

const props = withDefaults(defineProps<{
  device?: WorkspaceDevice;
  /** 仅在 dev_server_status 为 ready 时传入，值即 origin。 */
  src?: string;
  phase?: PreviewPhase;
  /** 正在等第一次响应，或状态是 starting。starting 不是失败。 */
  waiting?: boolean;
  busy?: boolean;
}>(), {
  device: 'desktop',
  src: '',
  phase: 'pending',
  waiting: false,
  busy: false,
});

const placeholder = computed(() => PLACEHOLDER[props.phase]);
</script>

<style lang="postcss" scoped>
.preview-canvas {
  display: flex;
  flex: 1;
  align-items: stretch;
  justify-content: center;
  min-width: 0;
  min-height: 0;
  background: #fff;
}

.preview-frame {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-width: 0;
  overflow: hidden;
  background: #fff;
}

.preview-frame--mobile {
  flex: 0 1 auto;
  width: min(390px, 100%);
  margin: 16px auto;
  border: 1px solid var(--line, #e4e9f1);
  border-radius: 16px;
}

.preview-frame__marquee {
  position: relative;
  flex-shrink: 0;
  height: 2px;
  overflow: hidden;
}

.preview-frame__marquee.is-active {
  background: #edf1ff;
}

.preview-frame__marquee-bar {
  display: none;
}

.preview-frame__marquee.is-active .preview-frame__marquee-bar {
  display: block;
  position: absolute;
  top: 0;
  left: 0;
  width: 36%;
  height: 100%;
  background: linear-gradient(90deg, transparent, #3d6dff 30%, #7b96ff 70%, transparent);
  animation: preview-marquee 1.1s ease-in-out infinite;
}

@keyframes preview-marquee {
  0% {
    transform: translateX(-100%);
  }

  100% {
    transform: translateX(380%);
  }
}

.preview-frame__body {
  display: flex;
  flex: 1;
  min-height: 0;
  background: #fff;
}

.preview-frame__iframe {
  width: 100%;
  height: 100%;
  border: 0;
}

.preview-frame__empty {
  display: flex;
  flex: 1;
  align-items: center;
  justify-content: center;
  padding: 24px;
  color: var(--faint, #88919e);
  text-align: center;
}
</style>
