<template>
  <span class="live-dot" :class="{ 'is-live': live }" />
</template>

<script setup lang="ts">
defineProps<{
  /** 还在动就是闪烁的蓝点；停住了（比如回放里被打断的那一段）是一颗不动的灰点。 */
  live?: boolean;
}>();
</script>

<style lang="postcss" scoped>
.live-dot {
  display: inline-block;
  flex-shrink: 0;
  width: 7px;
  height: 7px;
  background: #b6bdc9;
  border-radius: 50%;
}

.live-dot.is-live {
  background: #2f5bff;
  animation: live-dot-pulse 1.2s ease-in-out infinite;
}

@keyframes live-dot-pulse {
  0%,
  100% {
    opacity: 0.25;
  }

  50% {
    opacity: 1;
  }
}

@media (prefers-reduced-motion: reduce) {
  .live-dot.is-live {
    animation: none;
  }
}
</style>
