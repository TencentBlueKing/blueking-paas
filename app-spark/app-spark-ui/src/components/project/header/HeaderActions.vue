<template>
  <div class="header-actions">
    <UserInfo />
  </div>
</template>

<script setup lang="ts">
import UserInfo from '@/components/user-info.vue';
</script>

<style lang="postcss" scoped>
.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.header-actions :deep(.user-name) {
  color: #dcdee5;
}
</style>
