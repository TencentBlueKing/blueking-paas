<template>
  <div :class="['sandbox-log-box', { flex: isEmpty }]">
    <div
      v-if="isEmpty"
      class="empty-box"
    >
      <!-- <img src="/static/images/empty-dark.png" /> -->
      <table-empty
        empty
        :empty-title="$t('暂无日志')"
      />
    </div>

    <template v-else>
      <!-- 构建日志 -->
      <log-card
        class="log-card-box"
        :title="$t('构建日志')"
        :logs="buildLog"
        v-bind="$attrs"
      />
      <!-- 运行日志 -->
      <log-card
        :title="$t('运行日志')"
        class="log-card-box"
        :logs="runLog"
        v-bind="$attrs"
      />
    </template>
  </div>
</template>

<script>
import logCard from './log-card.vue';
export default {
  name: 'SandboxLog',
  components: { logCard },
  props: {
    buildLog: {
      type: String,
      default: '',
    },
    runLog: {
      type: String,
      default: '',
    },
  },
  data() {
    return {};
  },
  computed: {
    isEmpty() {
      return !this.buildLog.length && !this.runLog.length;
    },
  },
};
</script>

<style lang="scss" scoped>
.sandbox-log-box {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 16px;
  background: #313238;
  &.flex {
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .log-card-box {
    flex: 1;
    &.collapsed {
      flex: 0 0 32px;
    }
    &:first-child {
      /deep/ .logs-box {
        margin-bottom: 16px;
      }
    }
  }
}
</style>
