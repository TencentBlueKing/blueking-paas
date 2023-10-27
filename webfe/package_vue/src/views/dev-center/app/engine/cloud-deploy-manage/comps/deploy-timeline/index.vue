<template>
  <ul
    class="paas-deploy-timeline"
    :class="extCls"
    :style="{ width: `${width}px` }"
  >
    <li
      v-for="(item, index) in list"
      :key="index"
      class="paas-timeline-dot"
      :class="['paas-timeline-dot', makeClass(item, index)]"
      @click="toggle(item)"
      @mouseenter="handleMouseenter(item)"
      @mouseleave="handleMouseleave(item)"
    >
      <template v-if="isNeedIconcool(item)">
        <round-loading
          v-if="item.loading"
          ext-cls="paas-deploy-timeline-loading"
        />
        <div
          v-else
          class="paas-timeline-icon"
        >
          <i
            :class="['paasng-icon', `paasng-deploy-${item.stage}`]"
            :style="{ color: computedIconColor(item) }"
          />
        </div>
      </template>
      <template v-else>
        <round-loading
          v-if="item.status === 'pending'"
          ext-cls="paas-deploy-timeline-loading"
        />
        <div
          v-else
          class="paas-timeline-node-icon"
          :class="item.status"
        />
      </template>

      <div class="paas-timeline-section">
        <div
          v-if="item.tag !== ''"
          :class="[
            'paas-timeline-title',
            { 'is-weight': !!item.stage },
            { 'is-default': item.status === 'default' && !item.stage }
          ]"
        >
          <template v-if="item.status === 'skip'">
            <s style="color: #c4c6cc;">{{ item.tag }}</s>
          </template>
          <template v-else>
            {{ item.tag }}
          </template>
        </div>
        <div
          v-if="item.content"
          class="paas-timeline-content"
        >
          {{ item.content }}
        </div>
      </div>
    </li>
  </ul>
</template>
<script>
// 当前节点的5种状态: successful: 成功, failed: 失败, pending: 当前进行中, skip: 跳过, default: 默认(未开始)
const NODE_STATUS = ['successful', 'failed', 'pending', 'skip', 'default'];
export default {
  name: '',
  props: {
    list: {
      type: Array,
      required: true,
    },
    // 外部设置的 class name
    extCls: {
      type: String,
      default: '',
    },
    width: {
      type: Number,
      default: 230,
    },
    // 当前处于的阶段: noDeploy: 未部署，deploy: 部署中
    stage: {
      type: String,
      default: 'noDeploy',
    },
    disabled: {
      type: Boolean,
      default: true,
    },
  },
  data() {
    return {
      statusReg: /default|successful|failed|pending|skip/,
      stageList: ['build', 'preparation', 'release'],
      curHoverItem: {},
      curSelectedItem: {},
    };
  },
  computed: {
    isNeedIconcool() {
      return payload => payload.stage !== '' && this.stageList.includes(payload.stage);
    },
  },
  watch: {
    list: {
      handler() {
        this.$nextTick(() => {
          this.toggle(this.list[0]);
        });
      },
      immediate: true,
      deep: true,
    },
  },
  created() {
    this.nodeStatus = NODE_STATUS;
  },
  methods: {
    handleMouseenter(item) {
      if (this.disabled) {
        return;
      }
      if (item.stage) {
        this.curHoverItem = Object.assign({}, item);
      } else if (item.parentStage) {
        const match = this.list.find(timelineItem => timelineItem.stage === item.parentStage);
        if (match) {
          this.curHoverItem = Object.assign({}, match);
        }
      }
    },

    handleMouseleave() {
      if (this.disabled) {
        return;
      }

      this.curHoverItem = {};
    },

    /**
     * 部署开始后如果在部署准备阶段就失败的话，此时整个进程状态未变，获取未变的状态
     */
    handleGetIsInit() {
      return this.list.every(item => item.status === 'default') || this.list[0].status === 'pending';
    },

    handleResetStatus() {
      this.list.forEach((item) => {
        item.status = 'default';
        item.content = '';
        // eslint-disable-next-line no-prototype-builtins
        if (item.hasOwnProperty('loading')) {
          item.loading = false;
        }
      });
      this.curSelectedItem = {};
      this.curHoverItem = {};
    },

    /**
     * 部署发生错误结束时，当sse没有返回失败的数据时需手动设置处于pending状态的进程的状态为失败
     */
    handleSetFailed() {
      const pendingStage = this.list.filter(item => item.status === 'pending');
      if (pendingStage.length > 0) {
        const pendingIndex = pendingStage.length - 1;
        const pendingItem = this.list[pendingIndex];
        pendingItem.status = 'failed';
        pendingItem.content = '';
      }
    },

    /**
             * 部署发生错误结束时，获取失败的进程
             */
    handleGetFailed() {
      const pendingItem = this.list.find(item => item.status === 'failed');
      return pendingItem || {};
    },

    /**
             * 判断整个部署是否成功
             */
    handleGetIsSuccessful() {
      const lastItem = this.list[this.list.length - 1];
      return lastItem.status === 'successful';
    },

    computedIconColor({ status }) {
      const colorMap = {
        default: '#dcdee5',
        successful: '#18C0A1',
        failed: '#ea3636',
        pending: '#3a84ff',
      };
      if (['default', 'successful', 'failed', 'pending'].includes(status)) {
        return colorMap[status];
      }
      return '#dcdee5';
    },

    editNodeStatus(name, status, content) {
      const isMainStage = ['build', 'release', 'preparation'].includes(name);
      // console.log('this.list', this.list, name, status);
      const curNode = this.list.find(item => item.name === name);
      if (curNode) {
        curNode.status = status;
        curNode.content = content;
        if (isMainStage) {
          const childrenStage = this.list.filter(item => item.parentStage === name);
          const isAllDefault = (childrenStage || []).every(item => item.status === 'default');
          // 只有当子节点都未 loading, 并且父节点的状态正常时, 父节点才 loading.
          curNode.loading = curNode.status !== 'failed' && isAllDefault;
          if (name === 'build') {
            const preparationStage = this.list.find(item => item.stage === 'preparation');
            if (preparationStage && preparationStage.status === 'pending') {
              preparationStage.loading = false;
              preparationStage.status = 'successful';
            }
          }
          if (name === 'release') {
            const buildStage = this.list.find(item => item.stage === 'build');
            if (buildStage && buildStage.status === 'pending') {
              buildStage.loading = false;
              buildStage.status = 'successful';
            }
          }
        } else {
          const parentStage = this.list.find(item => item.name === curNode.parentStage);
          if (parentStage) {
            parentStage.loading = false;
          }
        }
      }
    },

    toggle(item) {
      if (this.disabled) {
        return;
      }

      if (item.stage) {
        this.curSelectedItem = Object.assign({}, item);
      } else if (item.parentStage) {
        const match = this.list.find(timelineItem => timelineItem.stage === item.parentStage);
        if (match) {
          this.curSelectedItem = Object.assign({}, match);
        }
      }
      this.$emit('select', this.curSelectedItem);
    },

    handleClick(item) {
      // 点击目录
      if (item.stage) {
        this.$emit('stage-click', item.display_blocks);
      }
    },

    makeClass(templateData) {
      const classPrefix = 'paas-timeline-item-';
      const classNames = [];

      if (templateData && templateData.status && this.statusReg.test(templateData.status)) {
        if (['successful', 'failed', 'pending'].includes(templateData.status)) {
          classNames.push(`${classPrefix}${templateData.status}`);
        } else {
          classNames.push(`${classPrefix}default`);
        }
      }

      if (!this.disabled) {
        if (templateData.stage) {
          classNames.push('stage-item');
        }
        if (templateData.parentStage) {
          classNames.push('step-item');
        }
        if (templateData.stage && templateData.stage === this.curSelectedItem.stage) {
          classNames.push('active-stage-item');
        }
        if (templateData.stage && templateData.stage === this.curHoverItem.stage) {
          classNames.push('active-stage-item');
        }
        if (templateData.parentStage && templateData.parentStage === this.curSelectedItem.stage) {
          classNames.push('active-step-item');
        }
        if (templateData.parentStage && templateData.parentStage === this.curHoverItem.stage) {
          classNames.push('active-step-item');
        }
      }
      return classNames;
    },
  },
};
</script>
<style lang="scss" scoped>
    $nodeSize: 11px;
    $largeNodeSize: 15px;

    .paas-deploy-timeline {
        list-style: none;
        padding: 0;

        .paas-timeline-dot {
            position: relative;
            padding: 8px 0 8px 30px;
            font-size: 0;

            &:last-child {
                &::after {
                    border: none;
                }
            }

            &::after {
                content: '';
                display: inline-block;
                width: 10px;
                height: 100%;
                border-left: 1px dashed #d8d8d8;
                position: absolute;
                left: 15px;
                top: 15px;
                z-index: 1;
            }

            .paas-timeline-title {
                display: inline-block;
                max-width: 200px;
                font-size: 14px;
                color: #63656e;
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
                vertical-align: top;
                &.is-weight {
                    font-weight: 700;
                }
                &.is-default {
                    color: #979ba5;
                }
            }
            .paas-timeline-content {
                display: inline-block;
                font-size: 14px;
                color: #c4c6cc;
                vertical-align: top;
            }
            .paas-timeline-icon {
                position: absolute;
                top: 50%;
                left: 6px;
                background: #fff;
                transform: translateY(-50%);
                z-index: 10;
                border-top: 2px solid #FFF;
                border-bottom: 2px solid #FFF;
                transition: all ease 0.3s;

                i {
                    font-size: 18px;
                }
                &.is-hover {
                    background: #e1ecff;
                }
            }
            .paas-deploy-timeline-loading {
                position: absolute;
                top: 50%;
                left: 7px;
                transform: translateY(-50%);
                background: #FFF;
                z-index: 10;
                border-top: 2px solid #FFF;
                border-bottom: 2px solid #FFF;
            }
            .paas-timeline-node-icon {
                position: absolute;
                left: 11px;
                top: 50%;
                z-index: 10;
                border-top: 2px solid #FFF;
                border-bottom: 2px solid #FFF;
                background: #FFF;
                display: inline-block;
                transform: translateY(-50%);

                &::after {
                    width: 9px;
                    height: 9px;
                    display: inline-block;
                    content: '';
                    border-radius: 50%;
                    border: 1px solid #dcdee5;
                    background: #f0f1f5;
                }

                &.skip {
                    &::after {
                        border-color: #ff9c01;
                        background: #ffd695;
                    }
                }
                &.successful {
                    &::after {
                        border-color: #18c0a1;
                        background: #a0f5e3;
                    }
                }
                &.failed {
                    &::after {
                        border-color: #ea3636;
                        background: #fd9c9c;
                    }
                }
                &.default {
                    &::after {
                        border-color: #dcdee5;
                        background: #f0f1f5;
                    }
                }
            }

            .paas-timeline-section {
                display: flex;
                justify-content: space-between;
                position: relative;
            }

            &.stage-item {
                cursor: pointer;
                background: #FFF;
                transition: all ease 0.3s;

                &:hover,
                &.active-stage-item {
                    background: #E1ECFF;
                    border-radius: 2px;

                    .paas-timeline-icon {
                        background: #E1ECFF;
                        border-color: #E1ECFF;
                        color: #3A84FF;

                        .paasng-icon {
                            color: #3A84FF !important;
                        }
                    }
                }
            }

            &.step-item {
                cursor: pointer;
                background: #FFF;
                transition: all ease 0.3s;

                &.active-step-item {
                    background: #f3f7fe;

                    .paas-timeline-node-icon {
                        background: #f3f7fe;
                        border-color: #f3f7fe;
                    }
                }
            }
        }

        .paas-timeline-item-default {
            &::after {
                border-color: #dcdee5;
            }
        }

        .paas-timeline-item-successful {
            &::after {
                border-color: #18c0a1;
            }
        }

        .paas-timeline-item-pending {
            &::after {
                border-color: #18c0a1;
            }
        }

        .paas-timeline-item-failed {
            &::after {
                border-color: #ea3636;
            }
        }
    }
</style>
