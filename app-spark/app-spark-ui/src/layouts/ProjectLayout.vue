<template>
  <div class="project-layout">
    <AppHeader />
    <main class="project-body">
      <slot />
    </main>
  </div>
</template>

<script setup lang="ts">
import AppHeader from '@/components/layout/AppHeader.vue';
</script>

<style lang="postcss" scoped>
.project-layout {
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
  color: var(--ink);
}

.project-body {
  display: flex;
  flex: 1;
  min-height: 0;
  background: var(--canvas);
}

@media (max-width: 760px) {
  .project-body {
    flex-direction: column;
    overflow-y: auto;
    scroll-snap-type: y proximity;
  }

  .project-body :deep(.interaction-panel),
  .project-body :deep(.workspace-panel) {
    flex: 0 0 calc(100vh - var(--nav-h));
    width: 100%;
    min-width: 0;
    min-height: 0;
    scroll-snap-align: start;
  }

  .project-body :deep(.interaction-panel) {
    border-right: 0;
    border-bottom: 1px solid var(--line);
  }
}
</style>
