<template>
  <div class="studio-header">
    <AppBreadcrumb class="studio-header__left" />
    <EnvStatus class="studio-header__center" />
    <HeaderActions class="studio-header__right" />
  </div>
</template>

<script setup lang="ts">
import AppBreadcrumb from './AppBreadcrumb.vue';
import EnvStatus from './EnvStatus.vue';
import HeaderActions from './HeaderActions.vue';
</script>

<style lang="postcss" scoped>
.studio-header {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  min-width: 0;
  padding-right: 16px;
}

.studio-header__center {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
}
</style>
