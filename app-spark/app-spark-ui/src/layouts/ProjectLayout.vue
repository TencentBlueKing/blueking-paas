<template>
  <div class="project-layout">
    <bk-navigation
      class="project-nav"
      navigation-type="top-bottom"
      side-title="App-Spark"
      :need-menu="false"
      :head-height="56"
      @click="handleNavClick"
    >
      <template #side-icon>
        <TreeApplicationShape />
      </template>
      <template #header>
        <StudioHeader />
      </template>
      <div class="project-body">
        <slot />
      </div>
    </bk-navigation>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router';
import { TreeApplicationShape } from 'bkui-vue/lib/icon';
import StudioHeader from '@/components/project/header/StudioHeader.vue';

const router = useRouter();

const handleNavClick = (event: MouseEvent) => {
  const target = event.target as HTMLElement;
  if (target.closest('.bk-navigation-title')) {
    router.push({ name: 'home' });
  }
};
</script>

<style lang="postcss" scoped>
.project-layout {
  --ink: #12141a;
  --muted: #5c6573;
  --faint: #88919e;
  --line: #e4e9f1;
  --canvas: #ffffff;
  --surface: #ffffff;
  --accent: #3d6dff;
  --accent-soft: #eef2ff;
  --rail-h: 56px;
  height: 100vh;
  color: var(--ink);
}

.project-nav {
  height: 100%;
}

.project-body {
  display: flex;
  height: 100%;
  min-height: 0;
  background: var(--canvas);
}

:deep(.bk-navigation-wrapper) {
  height: calc(100vh - 56px);
}

:deep(.bk-navigation-wrapper .navigation-container) {
  max-width: none;
}

:deep(.navigation-container .container-content) {
  padding: 0;
  max-width: none;
  height: 100%;
}

:deep(.bk-navigation-title) {
  flex-basis: 200px;
  cursor: pointer;
  border-bottom: none;
}

:deep(.bk-navigation-title .title-icon) {
  color: #6aa1ff;
}

:deep(.bk-navigation-title .title-desc) {
  color: #fff;
  font-weight: 600;
  letter-spacing: -0.02em;
}

:deep(.bk-navigation-header .header-right) {
  flex: 1;
  min-width: 0;
}
</style>
