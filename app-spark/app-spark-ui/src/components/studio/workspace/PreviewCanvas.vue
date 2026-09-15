<template>
  <div class="preview-canvas">
    <div :class="['preview-frame', `preview-frame--${device}`]">
      <div class="preview-frame__chrome">
        <span class="preview-frame__dot preview-frame__dot--red" />
        <span class="preview-frame__dot preview-frame__dot--yellow" />
        <span class="preview-frame__dot preview-frame__dot--green" />
        <span class="preview-frame__url">{{ src }}</span>
      </div>
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
  min-height: 0;
  padding: 16px;
  background: #f0f1f5;
}

.preview-frame {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: #fff;
  border: 1px solid #dcdee5;
  border-radius: 8px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.06);
}

.preview-frame--desktop {
  width: min(1100px, 100%);
}

.preview-frame--mobile {
  width: 390px;
}

.preview-frame__chrome {
  display: flex;
  align-items: center;
  gap: 6px;
  height: 36px;
  padding: 0 12px;
  background: #f5f7fa;
  border-bottom: 1px solid #dcdee5;
}

.preview-frame__dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.preview-frame__dot--red {
  background: #ea3636;
}

.preview-frame__dot--yellow {
  background: #ffb848;
}

.preview-frame__dot--green {
  background: #2dcb56;
}

.preview-frame__url {
  flex: 1;
  height: 22px;
  padding: 0 10px;
  color: #979ba5;
  line-height: 22px;
  background: #fff;
  border-radius: 11px;
}

.preview-frame__marquee {
  position: relative;
  height: 3px;
  overflow: hidden;
  background: transparent;
}

.preview-frame__marquee.is-active {
  background: #d4e6ff;
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
  background: linear-gradient(90deg, transparent, #3a84ff 30%, #5b9dff 70%, transparent);
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
  min-height: 520px;
  border: 0;
}

.preview-frame__empty {
  display: flex;
  flex: 1;
  align-items: center;
  justify-content: center;
  min-height: 520px;
  padding: 24px;
  color: #979ba5;
  text-align: center;
}
</style>
