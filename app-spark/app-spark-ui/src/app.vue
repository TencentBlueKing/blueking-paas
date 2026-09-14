<script setup lang="ts">
import {
  ref,
} from 'vue';
import { useUser } from '@/store/user';
import { getUserInfo } from '@/http/api';
import { redirectToLogin } from '@/common/auth';
import { Message } from 'bkui-vue';

const isLoading = ref(true);
const user = useUser();

const applyUserInfo = async () => {
  try {
    const data = await getUserInfo();
    if (data.authenticated) {
      user.setUser({
        authenticated: true,
        username: data.username,
        display_name: data.display_name,
        tenant_id: data.tenant_id,
      });
      isLoading.value = false;
      return;
    }
    redirectToLogin((data as { login_url?: string }).login_url || '');
  } catch (error: any) {
    const loginUrl = error?.response?.login_url;
    if (loginUrl) {
      redirectToLogin(loginUrl);
      return;
    }
    isLoading.value = false;
    Message('获取用户信息失败，请检查后再试');
  }
};

applyUserInfo();
</script>

<template>
  <bk-loading
    :loading="isLoading"
    :class="{
      'main-loading': isLoading
    }"
  >
    <router-view v-if="!isLoading"></router-view>
  </bk-loading>
</template>

<style lang="postcss" scoped>
  .main-loading {
    margin-top: 25vw;
  }
</style>
