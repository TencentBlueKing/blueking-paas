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
      <round-loading
        v-if="LOADING_MAP.includes(item.status)"
        ext-cls="paas-deploy-timeline-loading"
      />
      <!-- 无图标默认圆点样式 -->
      <div
        v-else
        class="paas-timeline-node-icon"
        :class="item.status"
      />

      <div class="paas-timeline-section">
        <div
          v-if="item.tag !== ''"
          :class="[
            'paas-timeline-title',
            { 'is-weight': !!item.stage },
            { 'is-default': item.status === 'default' && !item.stage },
          ]"
        >
          {{ item.tag }}
        </div>
        <div
          v-if="item.content && !hideTime.includes(item.status)"
          class="paas-timeline-content"
        >
          {{ item.content }}
        </div>
      </div>
    </li>
  </ul>
</template>
<script>export default {
  name: 'PaasDeployTimeline',
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
      stageList: ['build', 'preparation', 'release'],
      curHoverItem: {},
      curSelectedItem: {},
      // 插件loading 状态
      LOADING_MAP: ['QUEUE', 'RUNNING', 'REVIEWING', 'PREPARE_ENV', 'LOOP_WAITING', 'CALL_WAITING'],
      // 无需展示时间
      hideTime: ['SKIP', 'UNEXEC'],
    };
  },
  watch: {
    list() {
      this.$nextTick(() => {
        this.toggle(this.list[0]);
      });
    },
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

    // 点击对应步骤
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

    // 添加class
    makeClass(templateData, index) {
      const classNames = [];

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
.paas-deploy-timeline {
  overflow-y: auto;
  list-style: none;
  padding: 0;
  padding-right: 5px;
  &::-webkit-scrollbar {
    width: 4px;
    background-color: lighten(transparent, 80%);
  }
  &::-webkit-scrollbar-thumb {
    height: 5px;
    border-radius: 2px;
    background-color: #C4C6CC;
  }

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
      border-top: 2px solid #fff;
      border-bottom: 2px solid #fff;
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
      background: #fff;
      z-index: 10;
      border-top: 2px solid #fff;
      border-bottom: 2px solid #fff;
    }
    .paas-timeline-node-icon {
      position: absolute;
      left: 11px;
      top: 50%;
      z-index: 10;
      border-top: 2px solid #fff;
      border-bottom: 2px solid #fff;
      background: #fff;
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

      &.QUEUE,
      &.RUNNING,
      &.REVIEWING,
      &.PREPARE_ENV,
      &.LOOP_WAITING,
      &.CALL_WAITING {
        // 展示loading
        &::after {
          background: #90c2f8;
          border-color: #459fff;
        }
      }
      &.UNEXEC {
        &::after {
          background: #f0f1f5;
          border-color: #c4c6cc;
        }
      }

      &.CANCELED,
      &.REVIEW_ABORT,
      &.TRY_FINALLY,
      &.QUEUE_CACHE {
        &::after {
          background: #f2d8a4;
          border-color: #f6b026;
        }
      }
      &.FAILED,
      &.TERMINATE,
      &.HEARTBEAT_TIMEOUT,
      &.QUALITY_CHECK_FAIL,
      &.QUEUE_TIMEOUT,
      &.EXEC_TIMEOUT {
        &::after {
          background: #ffe6e6;
          border-color: #ea3636;
        }
      }
      &.SUCCEED,
      &.REVIEW_PROCESSED,
      &.STAGE_SUCCESS {
        &::after {
          border-color: #3fc06d;
          background: #e5f6ea;
        }
      }

      // skip
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
      background: #fff;
      transition: all ease 0.3s;

      &:hover,
      &.active-stage-item {
        background: #e1ecff;
        border-radius: 2px;

        .paas-timeline-icon {
          background: #e1ecff;
          border-color: #e1ecff;
          color: #3a84ff;

          .paasng-icon {
            color: #3a84ff !important;
          }
        }
      }
    }

    &.step-item {
      cursor: pointer;
      background: #fff;
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
}
</style>
