<template>
  <div :class="['preview-canvas', { 'is-mobile': device === 'mobile' }]">
    <div class="preview-canvas__bar">
      <div class="preview-bar" aria-label="预览浏览器工具栏">
        <button type="button" class="preview-bar__button" disabled aria-label="后退" title="跨域预览不支持后退">
          <AppIcon name="chevron-left" />
        </button>
        <button type="button" class="preview-bar__button" disabled aria-label="前进" title="跨域预览不支持前进">
          <AppIcon name="chevron-right" />
        </button>
        <button
          type="button"
          class="preview-bar__button device-toggle"
          :class="{ 'is-active': device === 'mobile' }"
          :aria-pressed="device === 'mobile'"
          :aria-label="device === 'mobile' ? '切换为桌面预览' : '切换为手机预览'"
          :title="device === 'mobile' ? '桌面预览' : '手机预览'"
          @click="$emit('update:device', device === 'mobile' ? 'desktop' : 'mobile')"
        >
          <AppIcon name="smartphone" />
        </button>
        <input
          class="preview-bar__address"
          type="text"
          :value="address"
          disabled
          :title="src || placeholder"
          aria-label="预览地址"
        >
        <a
          v-if="src"
          class="preview-bar__button"
          :href="src"
          target="_blank"
          rel="noopener"
          aria-label="在新标签页打开预览"
          title="在新标签页打开"
        >
          <AppIcon name="external-link" />
        </a>
        <span v-else class="preview-bar__button is-disabled" aria-hidden="true">
          <AppIcon name="external-link" />
        </span>
        <button
          type="button"
          class="preview-bar__button"
          :disabled="!src"
          aria-label="刷新预览"
          title="刷新预览"
          @click="$emit('refresh')"
        >
          <AppIcon name="rotate-cw" />
        </button>
      </div>
    </div>
    <div class="preview-stage">
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
            :key="frameKey"
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
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import AppIcon from '@/components/AppIcon.vue';
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
  /** src 不变时，靠它变化让 iframe 重新加载页面。 */
  frameKey?: number;
  phase?: PreviewPhase;
  /** 正在等第一次响应，或状态是 starting。starting 不是失败。 */
  waiting?: boolean;
  busy?: boolean;
}>(), {
  device: 'desktop',
  src: '',
  frameKey: 0,
  phase: 'pending',
  waiting: false,
  busy: false,
});

defineEmits<{
  (e: 'update:device', value: WorkspaceDevice): void;
  (e: 'refresh'): void;
}>();

const placeholder = computed(() => PLACEHOLDER[props.phase]);
const address = computed(() => props.src || placeholder.value);
</script>

<style lang="postcss" scoped>
.preview-canvas {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
  background: #fff;
}

.preview-canvas.is-mobile {
  background: var(--subtle-bg);
}

.preview-canvas__bar {
  flex-shrink: 0;
  padding: 10px 16px;
}

.preview-bar {
  display: flex;
  align-items: center;
  gap: 2px;
  height: 40px;
  padding: 0 6px;
  background: #fafbfc;
  border: 1px solid var(--line);
  border-radius: 12px;
}

.preview-bar__button {
  display: inline-flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  padding: 0;
  color: var(--muted);
  font-size: 18px;
  line-height: 1;
  text-decoration: none;
  background: transparent;
  border: 0;
  border-radius: 8px;
}

.preview-bar__button :deep(.app-icon) {
  font-size: 18px;
}

.preview-bar__button:not(:disabled, .is-disabled) {
  cursor: pointer;
}

.preview-bar__button:hover:not(:disabled, .is-disabled) {
  color: var(--ink);
  background: #eef1f6;
}

.preview-bar__button:disabled,
.preview-bar__button.is-disabled {
  color: #c9ced8;
  cursor: default;
}

.device-toggle.is-active,
.device-toggle.is-active:hover {
  color: var(--accent);
  background: var(--accent-soft);
}

.preview-bar__address {
  flex: 1;
  min-width: 0;
  height: 30px;
  margin: 0 4px;
  padding: 0 8px;
  color: var(--ink);
  font-family: var(--font-mono);
  font-size: 13px;
  text-overflow: ellipsis;
  background: transparent;
  border: 0;
  border-radius: 6px;
}

.preview-bar__address:focus {
  outline: none;
}

.preview-bar__button:focus-visible {
  outline: 2px solid var(--accent-focus);
  outline-offset: 1px;
}

.preview-stage {
  display: flex;
  flex: 1;
  justify-content: center;
  min-width: 0;
  min-height: 0;
}

.preview-frame {
  display: flex;
  flex-direction: column;
  width: 100%;
  min-width: 0;
  margin: 0;
  overflow: hidden;
  background: #fff;
  border-radius: 0;
  box-shadow: 0 0 0 0 transparent, 0 0 0 0 transparent;
}

.preview-frame--mobile {
  width: min(390px, calc(100% - 32px));
  margin: 16px 0;
  border-radius: 20px;
  box-shadow: 0 0 0 1px var(--line), 0 12px 32px rgba(16, 22, 34, 0.1);
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

@media (max-width: 760px) {
  .preview-canvas__bar {
    padding: 8px;
  }

  .preview-bar > button:nth-of-type(-n + 2) {
    display: none;
  }

  .preview-bar__address {
    margin-inline: 2px;
    font-size: 12px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .preview-frame__marquee.is-active .preview-frame__marquee-bar {
    animation: none;
  }
}
</style>
