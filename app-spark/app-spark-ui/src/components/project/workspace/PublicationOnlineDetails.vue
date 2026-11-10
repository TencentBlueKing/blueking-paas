<template>
  <div class="publication-online">
    <div class="publication-online__url">
      <AppIcon name="globe" />
      <a
        :href="online.url"
        :title="`在新标签页打开 ${online.url}`"
        target="_blank"
        rel="noopener noreferrer"
      >
        <span>{{ host }}</span>
        <AppIcon name="external-link" />
      </a>
      <button
        v-bk-tooltips="copied ? '已复制' : '复制访问地址'"
        type="button"
        :class="{ 'is-done': copied }"
        aria-label="复制访问地址"
        @click="$emit('copy')"
      >
        <AppIcon :name="copied ? 'check' : 'copy'" />
      </button>
    </div>
    <p class="publication-online__meta">
      <span class="publication-online__version-label">线上版本</span>
      <span
        class="publication-online__version-id"
        :title="online.version_id"
      >
        {{ online.version_id }}
      </span>
      <template v-if="online.published_at">
        <span class="publication-online__separator" aria-hidden="true">·</span>
        <span class="publication-online__published-at">{{ publishedText }}</span>
      </template>
    </p>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { fromNowFormatter } from '@/common/util';
import AppIcon from '@/components/AppIcon.vue';
import type { PublicationOnlineVersion } from '@/http/types';

const props = withDefaults(defineProps<{
  online: PublicationOnlineVersion;
  copied?: boolean;
}>(), {
  copied: false,
});
defineEmits<{ (e: 'copy'): void }>();

const host = computed(() => props.online.url.replace(/^https?:\/\//, '').replace(/\/$/, ''));
const publishedText = computed(() => {
  if (!props.online.published_at) return '';
  const relative = fromNowFormatter(props.online.published_at);
  return relative === '几秒前' ? '刚刚发布' : `发布于 ${relative}`;
});
</script>

<style lang="postcss" scoped>
.publication-online {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.publication-online__url {
  display: flex;
  align-items: center;
  gap: 8px;
  height: 36px;
  padding: 0 4px 0 10px;
  background: #f7f8fa;
  border: 1px solid var(--line);
  border-radius: 8px;
}

.publication-online__url > .app-icon {
  color: var(--publish);
  font-size: 15px;
}

.publication-online__url a {
  display: inline-flex;
  flex: 1;
  align-items: center;
  gap: 4px;
  min-width: 0;
  color: var(--accent);
  font-family: var(--font-mono);
  font-size: 12px;
  text-decoration: none;
  border-radius: 4px;
}

.publication-online__url a span {
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
  text-decoration: underline;
  text-decoration-color: rgba(61, 109, 255, 0.35);
  text-underline-offset: 3px;
  transition: text-decoration-color 120ms ease;
}

.publication-online__url a:hover {
  color: #1f46d6;
}

.publication-online__url a:hover span {
  text-decoration-color: currentColor;
}

.publication-online__url a .app-icon {
  flex-shrink: 0;
  font-size: 11px;
  opacity: 0.7;
}

.publication-online__url button {
  display: inline-flex;
  flex: 0 0 28px;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  padding: 0;
  color: var(--muted);
  font-size: 14px;
  background: transparent;
  border: 0;
  border-radius: 6px;
  cursor: pointer;
}

.publication-online__url button:hover {
  color: var(--ink);
  background: var(--hover-bg);
}

.publication-online__url button.is-done {
  color: #14a568;
}

.publication-online__url a:focus-visible,
.publication-online__url button:focus-visible {
  outline: 2px solid var(--accent-focus);
  outline-offset: 2px;
}

.publication-online__meta {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
  margin: 0;
  color: var(--faint);
  font-size: 12px;
  white-space: nowrap;
}

.publication-online__version-label,
.publication-online__separator,
.publication-online__published-at {
  flex-shrink: 0;
}

.publication-online__version-id {
  min-width: 0;
  overflow: hidden;
  font-family: var(--font-mono);
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
