<template>
  <div class="studio-header">
    <AppBreadcrumb class="studio-header__left" />
    <HeaderActions class="studio-header__right" />
  </div>
</template>

<script setup lang="ts">
import AppBreadcrumb from './AppBreadcrumb.vue';
import HeaderActions from './HeaderActions.vue';
</script>

<style lang="postcss" scoped>
.studio-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  min-width: 0;
  padding-right: 16px;
}
</style>
