<template>
  <ul class="version-timeline">
    <li
      v-for="item in versions"
      :key="item.id"
      :class="['version-timeline__item', { 'is-current': item.current }]"
    >
      <span class="version-timeline__dot" />
      <div class="version-timeline__content">
        <div class="version-timeline__title">
          {{ item.title }}
          <bk-tag v-if="item.current" theme="success">当前</bk-tag>
          <bk-tag v-else-if="item.tag" theme="info">{{ item.tag }}</bk-tag>
        </div>
        <p class="version-timeline__time">{{ item.time }}</p>
      </div>
    </li>
  </ul>
</template>

<script setup lang="ts">
import type { VersionItem } from './types';

defineProps<{
  versions: VersionItem[];
}>();
</script>

<style lang="postcss" scoped>
.version-timeline {
  padding: 16px;
}

.version-timeline__item {
  display: flex;
  gap: 10px;
  padding: 8px 0 16px;
}

.version-timeline__item.is-current {
  padding: 10px 12px;
  margin-bottom: 8px;
  background: var(--accent-soft, #edf1ff);
  border: 1px solid #c5d2ff;
  border-radius: 12px;
}

.version-timeline__dot {
  flex-shrink: 0;
  width: 8px;
  height: 8px;
  margin-top: 6px;
  background: #c4c6cc;
  border-radius: 50%;
}

.version-timeline__item.is-current .version-timeline__dot {
  background: var(--accent, #3d6dff);
  box-shadow: 0 0 0 3px rgba(61, 109, 255, 0.16);
}

.version-timeline__title {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  color: var(--ink, #12141a);
  font-size: 13px;
  line-height: 20px;
}

.version-timeline__time {
  margin: 4px 0 0;
  color: var(--faint, #88919e);
}
</style>
