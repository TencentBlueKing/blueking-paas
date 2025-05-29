<template>
  <div class="app-members-container">
    <!-- 复用普通应用成员管理页面 -->
    <Members />
  </div>
</template>

<script>
import Members from '@/views/dev-center/app/basic-config/members.vue';
export default {
  components: {
    Members,
  },
};
</script>
