<template>
  <div class="publication-failure-bar">
    <AppIcon name="info" />
    <span>
      {{ failure.is_update ? '最近一次更新版本' : '上次发布' }}
      <template v-if="failure.failed_at">（{{ fromNowFormatter(failure.failed_at) }}）</template>
      · 失败
    </span>
    <button type="button" @click="$emit('view')">查看</button>
  </div>
</template>

<script setup lang="ts">
import { fromNowFormatter } from '@/common/util';
import AppIcon from '@/components/AppIcon.vue';
import type { PublicationFailure } from '@/http/types';

defineProps<{ failure: PublicationFailure }>();
defineEmits<{ (e: 'view'): void }>();
</script>

<style lang="postcss" scoped>
.publication-failure-bar {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 7px 10px;
  color: #a33a33;
  font-size: 12px;
  background: var(--danger-soft);
  border: 1px solid #ffdcd6;
  border-radius: 8px;
}

.publication-failure-bar > .app-icon {
  flex: 0 0 14px;
  font-size: 14px;
}

.publication-failure-bar span {
  flex: 1;
  min-width: 0;
}

.publication-failure-bar button {
  padding: 0;
  color: var(--accent);
  font-size: 12px;
  background: transparent;
  border: 0;
  cursor: pointer;
}

.publication-failure-bar button:hover {
  text-decoration: underline;
  text-underline-offset: 3px;
}

.publication-failure-bar button:focus-visible {
  outline: 2px solid var(--accent-focus);
  outline-offset: 2px;
}
</style>
