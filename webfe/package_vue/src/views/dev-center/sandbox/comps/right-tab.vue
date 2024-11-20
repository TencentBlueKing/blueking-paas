<template>
  <div class="sandbox-rig-tab">
    <div
      :class="['floating-button', { expand: isExpand }]"
      slot="collapse-trigger"
      @click="handleSwitchSide"
    >
      <span :class="{ 'vertical-rl': localLanguage === 'en' }">{{ $t('查看配置和日志') }}</span>
      <i class="paasng-icon paasng-angle-line-up"></i>
    </div>
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
      isExpand: true,
    };
  },
  computed: {
    localLanguage() {
      return this.$store.state.localLanguage;
    },
  },
  methods: {
    handleTabChange(item) {
      this.active = item.name;
      this.$emit('tab-change', item.name);
    },
    handleSwitchSide() {
      this.isExpand = !this.isExpand;
      this.$emit('collapse-change', this.isExpand);
    },
  },
};
</script>

<style lang="scss" scoped>
.sandbox-rig-tab {
  display: flex;
  flex-direction: column;
  height: 100%;
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
  .floating-button {
    position: absolute;
    left: -24px;
    top: 50%;
    transform: translateY(-50%);
    width: 24px;
    padding: 11px 0;
    text-align: center;
    font-size: 12px;
    color: #63656e;
    line-height: 13px;
    background: #fafbfd;
    border: 1px solid #dcdee5;
    border-right: none;
    border-radius: 8px 0 0 8px;
    cursor: pointer;
    &.expand {
      i {
        transform: rotateZ(90deg);
      }
    }
    i {
      margin-top: 5px;
      color: #979ba5;
      transform: rotateZ(-90deg);
    }
    &:hover {
      color: #3a84ff;
      i {
        color: #3a84ff;
      }
    }
    .vertical-rl {
      writing-mode: vertical-rl;
    }
  }
}
</style>
