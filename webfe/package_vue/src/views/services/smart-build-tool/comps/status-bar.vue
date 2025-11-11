<template>
  <div :class="['status-indicator', `status-indicator--${status}`]">
    <div class="status-indicator-icon">
      <template v-if="['running', 'pending'].includes(status)">
        <round-loading />
      </template>
      <template v-else-if="['success', 'successful'].includes(status)">
        <i class="paasng-icon paasng-circle-correct-filled"></i>
      </template>
      <template v-else>
        <i class="paasng-icon paasng-close-circle-shape"></i>
      </template>
    </div>
    <div class="ml-8">
      <span class="status-text">{{ $t(statusText) }}</span>
      <bk-divider
        direction="vertical"
        class="ml-12 mr-12"
      ></bk-divider>
    </div>
    <div class="status-indicator__details">
      <span v-if="timeTaken">{{ `${$t('耗时')}：${timeTaken}` }}</span>
    </div>
    <div v-if="status === 'successful'">
      <bk-button
        text
        @click="handleAction('download')"
      >
        {{ $t('下载') }}
      </bk-button>
      <bk-button
        text
        class="ml10"
        @click="handleAction('back')"
      >
        {{ $t('返回') }}
      </bk-button>
    </div>
  </div>
</template>

<script>
export default {
  name: 'StatusIndicator',
  props: {
    status: {
      type: String,
      required: true,
      validator: (value) => ['running', 'success', 'failed'].includes(value),
    },
    timeTaken: {
      type: String,
      default: '',
    },
    showAction: {
      type: Boolean,
      default: true,
    },
  },
  computed: {
    statusText() {
      switch (this.status) {
        case 'running':
        case 'pending':
          return '执行中';
        case 'success':
        case 'successful':
          return '执行成功';
        case 'failed':
          return '执行失败';
        default:
          return '已中断';
      }
    },
  },
  methods: {
    handleAction(type) {
      this.$emit('action', type);
    },
  },
};
</script>

<style lang="scss" scoped>
.status-indicator {
  display: flex;
  align-items: center;
  padding: 10px 15px;
  border-radius: 2px;
  font-size: 12px;

  .status-text {
    font-size: 14px;
    color: #313238;
  }

  i.paasng-stop-2 {
    font-size: 16px;
  }

  .retry-icon {
    display: inline-block;
    width: 14px;
    height: 14px;
    border-radius: 50%;
    background-color: #3a84ff;
    i {
      color: #fff;
      font-size: 10px;
      transform: translateY(-3px);
    }
  }

  &--running,
  &--pending {
    background-color: #e1ecff;
  }

  &--success,
  &--successful {
    background-color: #daf6e5;

    .status-indicator-icon {
      font-size: 16px;
      color: #2caf5e;
    }
  }

  &--failed,
  &--interrupted {
    background-color: #ffebeb;

    .status-indicator-icon {
      font-size: 14px;
      color: #ea3636;
    }
  }

  &__details {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    flex-grow: 1;

    span {
      margin-right: 24px;
      white-space: nowrap;
    }
  }
}
</style>
