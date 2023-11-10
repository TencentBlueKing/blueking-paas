<template>
  <div class="build-stage">
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
  },
  data() {
    return {
      timeLineList: [],
      curBuilLog: '',
      isShowDate: false,
    };
  },
  computed: {
    curStages() {
      return this.stageData.detail.model.stages;
    },
  },
  watch: {
    isShowDate(value) {
      // 显示/隐藏时间
      this.$refs.bkLog.changeShowTime(value);
    },
  },
  created() {
    this.init();
  },
  methods: {
    init() {
      this.formatBuildLineData();
      this.formatLogs();
    },
    // 处理左侧数据
    formatBuildLineData() {
      // stages.length < 2 前端报错
      if (this.curStages.length === 2) {
        const { elements } = this.curStages[1].containers[0];
        // stages[1].containers[0].elements 左侧数据
        elements.forEach((v) => {
          const seconds = Math.floor(v.elapsed / 1000);
          this.timeLineList.push({
            content: `${seconds > 1 ? seconds : '<1'}s`,
            stage: '',
            status: v.status,
            tag: v.name,
          });
        });
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
  },
};
</script>

<style lang="scss" scoped>
.build-stage {
  height: calc(100vh - 218px);
  margin-top: 60px;
  display: flex;
  .right-log-wrapper {
    padding-top: 40px;
    margin-left: 16px;
    position: relative;
    overflow: hidden;
    flex: 1;
  }
  .paas-log-box {
    position: relative;
    overflow: hidden;
    padding: 0;
    height: calc(100vh - 258px);
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
  z-index: 99;
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
