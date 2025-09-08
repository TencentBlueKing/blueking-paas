<template lang="html">
  <div class="latest-updates-container flex-row flex-column">
    <h3 class="mb-16">{{ $t('最新动态') }}</h3>
    <bk-timeline
      v-if="operationsList.length"
      :list="timelineList"
    ></bk-timeline>
    <template v-else>
      <table-empty empty />
    </template>
  </div>
</template>

<script>
import { mapState, mapGetters } from 'vuex';

export default {
  props: {
    operationsList: {
      type: Array,
      default: () => [],
    },
  },
  computed: {
    ...mapState(['curAppInfo']),
    ...mapGetters(['isMultiTenantDisplayMode']),
    isEngineless() {
      return this.curAppInfo.web_config.engine_enabled;
    },
    timelineList() {
      const getContent = this.isMultiTenantDisplayMode
        ? (item) =>
            `<bk-user-display-name user-id="${item.operator}"></bk-user-display-name> ${this.formattedOperate(
              item.operate
            )}`
        : (item) => item.operate;
      return this.operationsList.map((item) => ({
        tag: item.at_friendly,
        content: getContent(item),
        type: 'primary',
      }));
    },
  },
  methods: {
    formattedOperate(operate) {
      return operate ? operate.split(' ').slice(1).join(' ') : '';
    },
  },
};
</script>

<style lang="scss" scoped>
.latest-updates-container {
  padding: 10px 16px 16px;
  h3 {
    font-weight: 700;
    font-size: 14px;
    color: #313238;
  }
}
</style>
