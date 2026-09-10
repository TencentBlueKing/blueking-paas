<template>
  <div class="studio-layout">
    <bk-navigation
      class="studio-nav"
      navigation-type="top-bottom"
      side-title="Vibe Studio"
      :need-menu="false"
      :head-height="56"
    >
      <template #side-icon>
        <TreeApplicationShape />
      </template>
      <template #header>
        <StudioHeader />
      </template>
      <div class="studio-body">
        <slot />
      </div>
    </bk-navigation>
  </div>
</template>

<script setup lang="ts">
import { TreeApplicationShape } from 'bkui-vue/lib/icon';
import StudioHeader from '@/components/studio/header/StudioHeader.vue';
</script>

<style lang="postcss" scoped>
.studio-layout {
  height: 100vh;
}

.studio-nav {
  height: 100%;
}

.studio-body {
  display: flex;
  height: 100%;
  min-height: 0;
  background: #f5f7fa;
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
  flex-basis: 180px;
  border-bottom: none;
}

:deep(.bk-navigation-title .title-icon) {
  color: #3a84ff;
}

:deep(.bk-navigation-title .title-desc) {
  color: #fff;
}

:deep(.bk-navigation-header .header-right) {
  flex: 1;
  min-width: 0;
}
</style>
