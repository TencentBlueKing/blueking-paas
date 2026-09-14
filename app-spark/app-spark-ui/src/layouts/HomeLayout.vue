<template>
  <div class="home-layout">
    <bk-navigation
      class="home-nav"
      navigation-type="top-bottom"
      side-title="App-Spark"
      :need-menu="false"
      :head-height="56"
    >
      <template #side-icon>
        <TreeApplicationShape />
      </template>
      <template #header>
        <div class="home-header">
          <UserInfo />
        </div>
      </template>
      <div class="home-body">
        <slot />
      </div>
    </bk-navigation>
  </div>
</template>

<script setup lang="ts">
import { TreeApplicationShape } from 'bkui-vue/lib/icon';
import UserInfo from '@/components/user-info.vue';
</script>

<style lang="postcss" scoped>
.home-layout {
  height: 100vh;
}

.home-nav {
  height: 100%;
}

.home-header {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  width: 100%;
  padding-right: 20px;
}

.home-header :deep(.user-name) {
  color: #d5d7de;
}

.home-header :deep(.user-name:hover),
.home-header :deep(.user-name:focus-visible) {
  color: #fff;
}

.home-body {
  min-height: 100%;
  padding: 8px clamp(20px, 4vw, 56px) 56px;
  background-color: #d9e3f2;
  background-image:
    radial-gradient(ellipse 72% 52% at 6% -4%, rgba(91, 132, 255, 0.5), transparent 56%),
    radial-gradient(ellipse 50% 40% at 96% 4%, rgba(56, 189, 248, 0.32), transparent 52%),
    radial-gradient(ellipse 58% 46% at 78% 108%, rgba(129, 140, 248, 0.28), transparent 58%),
    linear-gradient(168deg, #f3f6ff 0%, #dbe6f8 38%, #e3eef7 68%, #d5ebe6 100%);
  background-attachment: fixed;
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
  overflow: auto;
  background: transparent;
}

:deep(.bk-navigation-title) {
  flex-basis: 200px;
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
