<template>
  <div class="preview-canvas">
    <div
      :class="['preview-frame', `preview-frame--${device}`, { 'is-busy': busy }]"
    >
      <div
        class="preview-frame__marquee"
        :class="{ 'is-active': busy }"
        aria-hidden="true"
      >
        <span class="preview-frame__marquee-bar" />
      </div>
      <div class="preview-frame__body">
        <iframe
          v-if="ready"
          class="preview-frame__iframe"
          title="template 预览"
          :src="src"
        />
        <div v-else class="preview-frame__empty">
          模板服务启动中，请确认 template 已在 {{ src }} 运行…
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue';
import type { WorkspaceDevice } from './types';

const props = withDefaults(defineProps<{
  device?: WorkspaceDevice;
  src?: string;
  busy?: boolean;
}>(), {
  device: 'desktop',
  src: 'http://localhost:5173',
  busy: false,
});

const ready = ref(false);
let timer = 0;

const checkReady = async () => {
  try {
    await fetch(props.src, { mode: 'no-cors' });
    ready.value = true;
  } catch {
    ready.value = false;
  }
};

onMounted(() => {
  // 未配置生产预览时直接显示空白页，避免轮询无法 fetch 的 about: URL。
  if (props.src === 'about:blank') {
    ready.value = true;
    return;
  }
  checkReady();
  timer = window.setInterval(() => {
    if (!ready.value) {
      checkReady();
    }
  }, 1500);
});

onBeforeUnmount(() => {
  window.clearInterval(timer);
});
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
