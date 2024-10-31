<template>
  <div class="sandbox-rig-tab">
    <div class="tab-header">
      <div
        v-for="item in panels"
        :key="item.name"
        :class="['tab-item', { active: active === item.name }]"
        @click="handleTabChange(item)"
      >
        {{ item.label }}
      </div>
    </div>
    <div class="tab-content">
      <config-info
        v-show="active === 'config'"
        :data="data"
        v-bind="$attrs"
      />
      <log
        v-show="active === 'log'"
        v-bind="$attrs"
      />
    </div>
  </div>
</template>

<script>
import configInfo from './config-info.vue';
import log from './log.vue';
export default {
  components: { configInfo, log },
  name: 'SandboxTab',
  props: {
    data: {
      type: Object,
      default: () => {},
    },
  },
  data() {
    return {
      panels: [
        { name: 'config', label: this.$t('配置信息') },
        { name: 'log', label: this.$t('日志') },
      ],
      active: 'config',
    };
  },
  methods: {
    handleTabChange(item) {
      this.active = item.name;
      this.$emit('tab-change', item.name);
    },
  },
};
</script>

<style lang="scss" scoped>
.sandbox-rig-tab {
  display: flex;
  flex-direction: column;
  width: 360px;
  .tab-header {
    z-index: 9;
    flex-shrink: 0;
    display: flex;
    gap: 8px;
    .tab-item {
      flex: 1;
      display: flex;
      align-items: center;
      justify-content: center;
      height: 42px;
      background: #eaebf0;
      border-radius: 4px 4px 0 0;
      color: #63656e;
      cursor: pointer;
      &.active {
        background: #fff;
        color: #3a84ff;
      }
    }
  }
  .tab-content {
    flex: 1;
    height: calc(100% - 42px);
    background: #fff;
    box-shadow: 0 -2px 4px 0 #1919290d;
    border-radius: 2px;
  }
}
</style>
