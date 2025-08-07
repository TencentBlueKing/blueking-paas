<template>
  <div class="platform-step-guide mt-12">
    <!-- 步骤引导 -->
    <div class="guide-content ml-16">
      <div
        class="step"
        v-for="(step, index) in steps"
        :key="index"
      >
        <div class="step-title flex-row justify-content-between">
          <div>{{ step.title }}</div>
          <div
            v-if="step.code"
            class="icon-wrapper"
            v-copy="step.copyText || step.code"
          >
            <i class="paasng-icon paasng-general-copy"></i>
            {{ $t('复制') }}
          </div>
        </div>
        <div
          class="code-block"
          v-if="step.code"
        >
          <template v-if="Array.isArray(step.code)">
            <p
              v-for="(line, i) in step.code"
              :key="i"
              class="code"
            >
              {{ line }}
            </p>
          </template>
          <template v-else>
            <p class="code">{{ step.code }}</p>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'PlatformStepGuide',
  props: {
    steps: {
      type: Array,
      required: true,
      validator: (steps) => {
        return steps.every((step) => typeof step.title === 'string');
      },
    },
  },
  computed: {
    processedSteps() {
      return this.steps.map((step) => {
        return {
          ...step,
          codeLines: typeof step.code === 'string' ? [step.code] : Array.isArray(step.code) ? step.code : [],
        };
      });
    },
  },
};
</script>

<style lang="scss" scoped>
.platform-step-guide {
  .guide-title {
    font-weight: 700;
    font-size: 14px;
    color: #313238;
    margin-bottom: 12px;
  }
  .code-block {
    min-height: 52px;
    padding: 12px 16px;
    background: #f5f7fa;
    border-radius: 2px;
    line-height: 22px;
    font-family: Consolas, monospace, tahoma, Arial;
    font-size: 14px;
    color: #313238;
    .code {
      word-break: break-all;
      white-space: pre-line;
    }
  }
  .step {
    position: relative;
    min-height: 52px;
    padding-bottom: 10px;
    .step-title {
      padding-bottom: 6px;
      .icon-wrapper {
        color: #3a84ff;
        cursor: pointer;
        font-size: 14px;
        i {
          font-size: 16px;
        }
      }
    }
    &::before {
      content: '';
      position: absolute;
      top: 5px;
      left: -15px;
      width: 9px;
      height: 9px;
      background: #fff;
      border: 2px solid #d8d8d8;
      border-radius: 50%;
      z-index: 1;
    }
    &::after {
      content: '';
      position: absolute;
      top: 5px;
      height: 100%;
      width: 1px;
      background-color: #d8d8d8;
      left: -11px;
    }
    &:last-child {
      &::after {
        display: none;
      }
    }
  }
}
</style>
