<template>
  <div class="sandbox-rig-tab">
    <div
      :class="['floating-button', { expand: isExpand }]"
      slot="collapse-trigger"
      @click="handleSwitchSide"
    >
      <i class="paasng-icon paasng-angle-line-up"></i>
    </div>
    <!-- 加载完毕显示运行操作 -->
    <div
      class="action-buts"
      v-if="isLoadComplete"
    >
      <template v-if="isRerun">
        <bk-button
          theme="primary"
          :outline="true"
          :loading="btnLoading"
          @click="$emit('rerun')"
        >
          <i class="paasng-refresh-line paasng-icon"></i>
          {{ $t('重新运行') }}
        </bk-button>
      </template>
      <template v-else>
        <bk-button
          theme="primary"
          :loading="btnLoading"
          bk-trace="{id: 'sandbox', action: 'run', category: '云原生应用'}"
          @click="$emit('run-now')"
        >
          <i class="paasng-right-shape paasng-icon"></i>
          {{ $t('立即运行') }}
        </bk-button>
      </template>
      <bk-button
        theme="default"
        @click="$emit('submit-code')"
      >
        {{ $t('提交代码') }}
      </bk-button>
    </div>
    <!-- 运行状态 -->
    <div
      class="run-tip success"
      v-if="isRerun && btnLoading"
    >
      <div class="status">
        <round-loading class="mr5" />
        {{ $t('运行中') }}
      </div>
    </div>
    <div
      v-else-if="isRerun || isShowStatus"
      :class="['run-tip', isShowLink ? 'success' : 'error']"
    >
      <div class="status">
        <i
          class="paasng-icon paasng-check-circle-shape"
          v-if="isShowLink"
        ></i>
        <i
          class="paasng-icon paasng-close-circle-shape"
          v-else
        ></i>
        {{ isShowLink ? $t('运行成功') : $t('运行失败') }}
      </div>
      <!-- 访问链接 -->
      <bk-button
        v-if="isShowLink"
        :theme="'primary'"
        text
        @click="$emit('jump')"
      >
        {{ $t('立即访问') }}
        <i class="paasng-jump-link paasng-icon"></i>
      </bk-button>
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
    <div
      class="tab-content"
      :style="{ height: `calc(100% - ${isShowStatus || isRerun ? '140px' : '110px'})` }"
    >
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

// body overflow 控制类名
const BODY_LOCK_CLASS = 'sandbox-overflow-hidden-body-lock';

export default {
  components: { configInfo, log },
  name: 'SandboxTab',
  props: {
    data: {
      type: Object,
      default: () => {},
    },
    // 加载完毕
    isLoadComplete: {
      type: Boolean,
      default: false,
    },
    isRerun: {
      type: Boolean,
      default: false,
    },
    btnLoading: {
      type: Boolean,
      default: false,
    },
    isShowStatus: {
      type: Boolean,
      default: false,
    },
    isBuildSuccess: {
      type: Boolean,
      default: false,
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
    isShowLink() {
      return this.isBuildSuccess || this.isRerun;
    },
  },
  mounted() {
    if (this.active === 'config') {
      this.toggleBodyOverflow(true);
    }
  },
  beforeDestroy() {
    this.removeBodyOverflow();
  },
  methods: {
    handleTabChange(item) {
      this.active = item.name;
      this.$emit('tab-change', item.name);
      // 配置页面禁止滚动、防止tooltips滚动导致页面出现滚动条
      this.toggleBodyOverflow(item.name === 'config');
    },
    handleSwitchSide() {
      this.isExpand = !this.isExpand;
      this.$emit('collapse-change', this.isExpand);
    },
    toggleBodyOverflow(hidden) {
      if (hidden) {
        document.body.classList.add(BODY_LOCK_CLASS);
      } else {
        document.body.classList.remove(BODY_LOCK_CLASS);
      }
    },
    removeBodyOverflow() {
      document.body.classList.remove(BODY_LOCK_CLASS);
    },
  },
};
</script>

<style lang="scss" scoped>
.sandbox-rig-tab {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #2e2e2e;
  .tab-header {
    z-index: 9;
    flex-shrink: 0;
    display: flex;
    .tab-item {
      flex: 1;
      display: flex;
      align-items: center;
      justify-content: center;
      height: 44px;
      font-size: 14px;
      color: #c4c6cc;
      background: #2e2e2e;
      cursor: pointer;
      &.active {
        background: #1a1a1a;
        font-weight: 700;
        border-top: 4px solid #3a84ff;
      }
    }
  }
  .tab-content {
    flex: 1;
    background: #1a1a1a;
    box-shadow: 0 -2px 4px 0 #1919290d;
    position: relative;
  }
  .floating-button {
    position: absolute;
    left: -20px;
    top: 50%;
    transform: translateY(-50%);
    height: 64px;
    width: 20px;
    text-align: center;
    font-size: 12px;
    line-height: 64px;
    background: #fafbfd;
    border-right: none;
    border-radius: 4px 0 0 4px;
    cursor: pointer;
    background-color: #dcdee5;
    &.expand {
      i {
        transform: rotateZ(90deg);
      }
    }
    i {
      margin-top: 5px;
      color: #fff;
      transform: rotateZ(-90deg);
    }
    &:hover {
      background-color: #3a84ff;
    }
  }
  .action-buts {
    flex-shrink: 0;
    height: 56px;
    margin-left: auto;
    padding: 0 16px;
    display: flex;
    align-items: center;
    gap: 16px;
    button {
      width: 156px;
      &.bk-default {
        background: #2e2e2e;
        color: #f0f1f5;
      }
      &.is-outline {
        background: #2e2e2e;
        color: #a3c5fd;
        &:hover {
          background-color: #3a84ff;
          color: #fff;
        }
      }
    }
  }
  .run-tip {
    flex-shrink: 0;
    height: 40px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 16px;
    color: #dcdee5;
    background: rgba(101, 195, 137, 0.4);
    .status {
      i {
        margin-right: 3px;
        color: #2caf5e;
      }
    }
    &.error {
      background: rgba(255, 86, 86, 0.4);
      .status i {
        color: #d26b6b;
      }
    }
    .bk-button-text {
      color: #a3c5fd;
    }
  }
}
</style>

<style lang="scss">
.sandbox-overflow-hidden-body-lock {
  overflow-y: hidden !important;
}
</style>
