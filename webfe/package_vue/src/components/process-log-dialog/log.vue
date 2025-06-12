<template>
  <transition name="dialog-fade">
    <!--进程日志 -->
    <div
      v-if="internalVisible"
      class="paas-log dialog-backdrop"
      @click.self="handleClose"
    >
      <div
        class="log-wrapper"
        @click.stop
      >
        <div class="log-header">
          <slot name="header">
            <!-- 默认日志样式 -->
            <div class="top">
              <div class="title">{{ title }}</div>
              <div class="config">
                <div class="group">
                  <div
                    v-for="item in logTypeOption"
                    :class="['item', { active: item.id === logType }]"
                    :key="item.key"
                    @click="changeLogType(item.id)"
                  >
                    {{ item.text }}
                  </div>
                </div>
              </div>
              <div class="tools">
                <bk-select
                  v-model="selectValue"
                  :clearable="false"
                  class="ml20"
                  ext-cls="log-time-select-cls"
                  :disabled="isDisabledRestartLog"
                  @selected="refresh"
                >
                  <bk-option
                    v-for="(option, i) in selectionList"
                    :id="option.id"
                    :key="i"
                    :name="option.name"
                  />
                  <bk-option
                    v-if="isDisabledRestartLog"
                    :id="'restart'"
                    :key="-1"
                    :name="$t('最近 400 条')"
                  />
                </bk-select>
                <!-- 刷新 -->
                <i
                  class="paasng-icon paasng-refresh ml20"
                  @click="refresh"
                ></i>
                <!-- 普通应用-实时日志不支持下载 -->
                <i
                  v-bk-tooltips="{ content: downloadNotSupported ? $t('暂不支持下载实时日志') : $t('下载完整日志') }"
                  class="paasng-icon paasng-download ml20"
                  :class="{ disabled: downloadNotSupported }"
                  @click="download"
                ></i>
              </div>
            </div>
          </slot>
        </div>
        <div
          class="log-content"
          v-bkloading="{ isLoading: loading, color: 'rgba(255, 255, 255, 0.1)', zIndex: 10 }"
        >
          <slot name="content">
            <bk-log
              v-if="logs.length"
              class="bk-log"
              ref="bkLog"
              :key="logIndex"
            ></bk-log>
            <div
              v-else
              class="empty"
            >
              {{ loading ? '' : $t('暂时没有日志记录') }}
            </div>
          </slot>
        </div>
      </div>
    </div>
  </transition>
</template>

<script>
import { bkLog } from '@blueking/log';

export default {
  name: 'PaasLog',
  components: {
    bkLog,
  },
  props: {
    value: {
      type: Boolean,
      required: true,
    },
    params: {
      type: Object,
      default: () => {},
    },
    title: {
      type: String,
      default: '',
    },
    loading: {
      type: Boolean,
      default: true,
    },
    selectionList: {
      type: Array,
      default: () => [],
    },
    defaultCondition: {
      type: String,
      default: '1h',
    },
    logs: {
      type: Array | String,
      default: () => [],
    },
    // 直接展示当前行日志
    isDirect: {
      type: Boolean,
      default: false,
    },
  },
  data() {
    return {
      internalVisible: this.value,
      selectValue: this.defaultCondition,
      logType: 'realtime',
      logIndex: 0,
      logTypeOption: [
        { id: 'realtime', text: this.$t('实时日志') },
        { id: 'restart', text: this.$t('最近一次重启日志') },
      ],
    };
  },
  computed: {
    isRealTimeLog() {
      return this.logType === 'realtime';
    },
    isDisabledRestartLog() {
      return this.logType === 'restart' && this.defaultCondition === '1h';
    },
    // 普通应用-实时日志不支持下载
    downloadNotSupported() {
      return this.logType === 'realtime' && this.defaultCondition === '1h';
    },
  },
  watch: {
    value(newVal) {
      this.internalVisible = newVal;
      this.init();
    },
    internalVisible(newVal) {
      this.$emit('input', newVal);
      if (newVal) {
        document.body.style.overflow = 'hidden';
      } else {
        document.body.style.overflow = '';
      }
    },
    logs: {
      handler(newLogs) {
        this.logIndex += 1;
        this.$nextTick(() => {
          this.$refs.bkLog.addLogData(newLogs);
        });
      },
      deep: true,
    },
  },
  methods: {
    handleClose() {
      this.internalVisible = false;
      this.$emit('close');
    },
    init() {
      this.selectValue = this.defaultCondition;
      this.logType = 'realtime';
    },
    // 切换日志类型
    changeLogType(type) {
      if (this.loading) return;
      this.logType = type;
      this.selectValue = this.isDisabledRestartLog ? 'restart' : this.defaultCondition;
      this.$emit('change', {
        type: this.logType,
        value: this.selectValue,
      });
    },
    // 刷新
    refresh() {
      this.$emit('refresh', {
        type: this.logType,
        value: this.selectValue,
      });
    },
    // 下载重启日志
    async download() {
      this.$emit('download', this.logType);
    },
  },
};
</script>

<style lang="scss" scoped>
.dialog-backdrop {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 2000;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  flex-direction: row-reverse;

  .log-wrapper {
    overflow: hidden;
    background-color: #1e1e1e;
    color: #fff;
    height: calc(100% - 32px);
    width: 80%;
    margin: 16px;
    border-radius: 6px;
    min-width: 300px;
    font-size: 12px;
    transition: all 0.2s ease-in-out; /* 对话框本身的过渡 */

    .log-header {
      background-color: #252935;
      border-bottom: 1px solid #2b2b2b;
      border-radius: 6px 6px 0 0;
      color: #d4d4d4;
      min-height: 48px;
      padding: 8px 20px;

      .top {
        height: 100%;
        display: flex;
        align-items: center;
        justify-content: space-between;
        flex-wrap: wrap;

        .config .group {
          display: flex;
          align-items: center;
          .item {
            background: #2e3342;
            color: #999;
            height: 26px;
            line-height: 26px;
            padding: 0 12px;
            cursor: pointer;
            border-radius: 3px 0 0 3px;

            &:last-child {
              border-radius: 0 3px 3px 0;
            }

            &.active {
              background: #1a6df3;
              color: #fff;
            }
          }
        }

        .tools {
          display: flex;
          align-items: center;
          .log-time-select-cls {
            background: hsla(0, 0%, 100%, 0.125);
            border: none;
            color: #f6f8fa;
            width: 200px;
            flex-shrink: 0;
          }
          i {
            font-size: 16px;
            cursor: pointer;
            &.disabled {
              cursor: not-allowed;
            }
          }
        }
      }
    }

    .log-content {
      height: calc(100% - 48px);
      .bk-log {
        height: 100%;
        transform: translateY(-5px);
        /deep/ .scroll-home .scroll-main .scroll-item {
          font-family: Consolas, Courier New, monospace;
          color: #fff !important;
        }
      }
      .empty {
        padding: 16px;
      }
    }
  }
}

/* 过渡动画 */
.dialog-fade-enter-active,
.dialog-fade-leave-active {
  transition: opacity 0.2s;
}

.dialog-fade-enter,
.dialog-fade-leave-to {
  opacity: 0;
}
</style>
