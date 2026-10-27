<script setup lang="ts">
import { ref } from 'vue';
import { useUser } from '@/store/user';
import { logout } from '@/common/auth';
import { AngleDownLine } from 'bkui-vue/lib/icon';

const user = useUser();
const userInfo = ref(user.user);
</script>

<template>
  <bk-popover
    class="user-home"
    placement="bottom-end"
    theme="light"
  >
    <button
      type="button"
      class="user-name"
      :aria-label="`账号菜单：${userInfo.display_name || userInfo.username || '当前用户'}`"
    >
      <span class="user-name__text">{{ userInfo.display_name || userInfo.username || '账号' }}</span>
      <angle-down-line />
    </button>
    <template #content>
      <button
        type="button"
        class="logout"
        @click="logout"
      >退出</button>
    </template>
  </bk-popover>
</template>

<style lang="postcss" scoped>
.user-name {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 0;
  color: inherit;
  cursor: pointer;
  font-size: 14px;
  background: transparent;
  border: 0;
}

.logout {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  width: 50px;
  height: 30px;
  padding: 0;
  color: var(--ink);
  cursor: pointer;
  font-size: 14px;
  background: transparent;
  border: 0;
  border-radius: 6px;
}

.user-name:focus-visible,
.logout:focus-visible {
  outline: 2px solid var(--accent-focus);
  outline-offset: 2px;
}
</style>
