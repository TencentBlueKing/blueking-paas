<template>
  <div class="header-actions">
    <bk-button text @click="handleHistory">
      <LeftTurnLine class="header-actions__icon" />
      历史
    </bk-button>
    <bk-button text @click="handlePreview">
      <Eye class="header-actions__icon" />
      预览
    </bk-button>
    <bk-button theme="primary" @click="handlePublish">
      发布上线
    </bk-button>
    <UserInfo />
  </div>
</template>

<script setup lang="ts">
import { Eye, LeftTurnLine } from 'bkui-vue/lib/icon';
import UserInfo from '@/components/user-info.vue';

const handleHistory = () => {};
const handlePreview = () => {};
const handlePublish = () => {};
</script>

<style lang="postcss" scoped>
.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.header-actions__icon {
  margin-right: 4px;
  font-size: 14px;
}

.header-actions :deep(.bk-button-text) {
  color: #dcdee5;
}

.header-actions :deep(.bk-button-text:hover) {
  color: #fff;
}

.header-actions :deep(.user-name) {
  color: #dcdee5;
}
</style>
