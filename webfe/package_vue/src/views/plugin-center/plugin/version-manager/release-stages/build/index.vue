<template>
  <div :class="['build-stage', { 'build-hide-button-group': !bottomActionBar }, bottomActionBar]">
    <build-timeline
      :list="timeLineList"
      :disabled="true"
      class="mt20 ml15 mr15"
      style="min-width: 250px"
    />
    <!-- 日志 -->
    <div class="right-log-wrapper">
      <section class="log-header">
        <bk-switcher
          v-model="isShowDate"
          :disabled="!curBuilLog.length"
          class="bk-small-switcher mr5"
        />
        <span class="text">{{ isShowDate ? $t('隐藏时间') : $t('显示时间') }}</span>
      </section>
      <div class="paas-log-box">
        <bk-log
          class="bk-log"
          ref="bkLog"
        ></bk-log>
      </div>
    </div>
  </div>
</template>
<script>import buildTimeline from './build-time-line.vue';
import stageBaseMixin from '../stage-base-mixin';
import { bkLog } from '@blueking/log';

export default {
  components: {
    buildTimeline,
    bkLog,
  },
  mixins: [stageBaseMixin],
  props: {
    pluginData: {
      type: Object,
      default: () => {},
    },
    stageData: {
      type: Object,
      default: () => {},
    },
    // 是否可执行下一步
    isNext: {
      type: Boolean,
      default: false,
    },
  },
  data() {
    return {
      timeLineList: [],
      curBuilLog: '',
      isShowDate: false,
      bottomActionBar: null,
    };
  },
  computed: {
    curStages() {
      return this.stageData.detail.model.stages;
    },
    // 是否存在后置阶段 (前端添加后置阶段)
    isPostCommand() {
      return this.pluginData.current_stage.has_post_command;
    },
  },
  watch: {
    isShowDate(value) {
      // 显示/隐藏时间
      this.$refs.bkLog.changeShowTime(value);
    },
    stageData() {
      // 重新格式化数据
      this.formatBuildLineData();
      this.formatLogs();
      this.setBottomActionBar();
    },
  },
  created() {
    this.init();
    this.setBottomActionBar();
  },
  methods: {
    init() {
      this.formatBuildLineData();
      this.formatLogs();
    },
    // 处理左侧数据
    formatBuildLineData() {
      this.timeLineList = [];
      // stages.length < 2 前端报错
      if (this.curStages.length === 2) {
        const { elements } = this.curStages[1].containers[0];
        // stages[1].containers[0].elements 左侧数据
        elements.forEach((v) => {
          if (v.additionalOptions?.elementPostInfo) return;
          const seconds = Math.floor(v.elapsed / 1000);
          this.timeLineList.push({
            content: `${seconds > 1 ? seconds : '<1'}s`,
            stage: '',
            status: v.status,
            tag: v.name,
          });
        });
        // 是否添加后置命令阶段
        if (this.isPostCommand) {
          let postCommandStatus = '';
          const { status } = this.stageData;
          if (status === 'successful') {
            postCommandStatus = this.isNext ? 'SUCCEED' : 'RUNNING';
          } else {
            // 执行后置命令
            postCommandStatus = 'POSTCOMMAND';
          }
          this.timeLineList.push({
            content: '',
            stage: '',
            status: postCommandStatus,
            tag: this.$t('执行后置命令'),
          });
        }
      }
    },
    formatLogs() {
      const { logs } = this.stageData.logs;
      this.curBuilLog = logs;
      this.$nextTick(() => {
        // 设置日志数据
        this.$refs.bkLog.addLogData(this.curBuilLog);
        this.$refs.bkLog.changeShowTime(this.isShowDate);
      });
    },
    setBottomActionBar() {
      this.bottomActionBar = document.querySelector('.footer-btn-warp');
    },
  },
};
</script>

<style lang="scss" scoped>
// 高度问题
.build-stage {
  display: flex;
  padding: 16px 16px 0;

  // 无按钮组
  &.build-hide-button-group {
    margin-bottom: 24px;
    .right-log-wrapper {
      padding-bottom: 16px;
    }
  }
  .right-log-wrapper {
    display: flex;
    flex-direction: column;
    min-height: 0;
    padding-top: 40px;
    margin-left: 16px;
    position: relative;
    overflow: hidden;
    flex: 1;
  }
  .paas-log-box {
    flex: 1;
    position: relative;
    overflow: hidden;
    padding: 0;
  }
}
.log-header {
  position: absolute;
  display: flex;
  align-items: center;
  padding: 0 20px;
  height: 40px;
  top: 0;
  left: 0;
  right: 0;
  background: #2A2B2F;
  border-bottom: 1px solid #000;
  color: #fff;
  border-radius: 2px 2px 0 0;
}
.bk-log {
  height: 100%;
  transform: translateY(-5px);
}
</style>
