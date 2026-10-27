<template>
  <div class="home-layout">
    <AppHeader />
    <div class="home-layout__shell">
      <AppSidebar />
      <main class="home-layout__content">
        <slot />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import AppHeader from '@/components/layout/AppHeader.vue';
import AppSidebar from '@/components/layout/AppSidebar.vue';
</script>

<style lang="postcss" scoped>
.home-layout {
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
}

.home-layout__shell {
  display: flex;
  flex: 1;
  min-height: 0;
}

.home-layout__content {
  flex: 1;
  min-width: 0;
  min-height: 100%;
  overflow: auto;
}
</style>
