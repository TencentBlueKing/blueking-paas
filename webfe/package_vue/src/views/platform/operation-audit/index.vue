<template>
  <div class="right-main operation-audit-container">
    <Record :type="tabActive" />
  </div>
</template>

<script>
import Record from './record';

export default {
  name: 'PlatformOperationAudit',
  components: {
    Record,
  },
  computed: {
    tabActive() {
      return this.$route.query.active || 'platform';
    },
  },
};
</script>

<style lang="scss" scoped>
.operation-audit-container {
  padding: 24px;
}
</style>
