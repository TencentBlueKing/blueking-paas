<template>
  <div>
    <section class="home-top-title">
      <div class="title">
        {{ $t('应用总览') }}
        <span class="tips">{{ $t('更新于 {t}之前', { t: appChartInfo.updateTime }) }}</span>
      </div>
      <div class="tools">
        <bk-select
          v-model="curDate"
          style="width: 137px"
          :clearable="false"
          ext-cls="date-select-cls"
          @change="handleDateChange"
        >
          <bk-option
            v-for="option in dateList"
            :key="option.id"
            :id="option.id"
            :name="option.label"
          ></bk-option>
        </bk-select>
        <bk-button
          :theme="'primary'"
          @click="toCreateApp"
        >
          {{ $t('创建应用') }}
        </bk-button>
      </div>
    </section>
    <div class="app-overview-container">
      <!-- 告警情况 -->
      <div
        class="alarm-status card-style"
        v-if="platformFeature.MONITORING"
      >
        <div class="card-title chart-title">
          {{ $t('告警情况') }}
        </div>
        <chart
          id="alarm-status"
          class="chart-el"
        ></chart>
        <div
          class="default-text"
          v-if="isAlarmLabel"
        >
          <p class="vlaue">{{ alarmDefaultLabel.value }}</p>
          <p class="name">{{ alarmDefaultLabel.name }}</p>
        </div>
        <!-- <div
          class="chart-el chart-alert"
          v-charts="alertChartOption"
        ></div> -->
      </div>
      <!-- 应用情况 -->
      <div class="app-status card-style">
        <div class="card-title chart-title">
          {{ $t('应用情况') }}
        </div>
        <chart
          id="chart-app-status"
          class="chart-el"
        ></chart>
        <div
          class="default-text"
          v-if="isAppLabel"
        >
          <p class="vlaue">{{ appDefaultLabel.value }}</p>
          <p class="name">{{ appDefaultLabel.name }}</p>
        </div>
      </div>
      <!-- 运维开发分 -->
      <!-- <div class="ops-dev-score card-style">
        <p class="card-title">运维开发分</p>
        <div class="info">
          <div>
            <span class="fraction">90</span>
            <span class="ml5">分</span>
          </div>
        </div>
      </div> -->
    </div>
  </div>
</template>

<script>
import alertChartOption from '@/json/home-page-chart-option';
import { formatDate } from '@/common/tools';
import { bus } from '@/common/bus';
import ECharts from 'vue-echarts/components/ECharts.vue';
import echarts from 'echarts';

export default {
  name: 'HomeAppOverview',
  components: {
    chart: ECharts,
  },
  data() {
    return {
      chartAppInfo: {
        total: 0,
        issueCount: 0,
      },
      curDate: 1,
      dateList: [
        { label: this.$t('1 天'), id: 1 },
        { label: this.$t('7 天'), id: 7 },
        { label: this.$t('15 天'), id: 15 },
        { label: this.$t('一个月'), id: 30 },
      ],
      curSelectionTime: this.getSpecifiedDate(1),
      appChart: null,
      alarmChart: null,
      // 应用情况默认值
      isAppLabel: true,
      // 告警情况默认显示控制
      isAlarmLabel: true,
    };
  },
  computed: {
    appChartInfo() {
      return this.$store.state.baseInfo.appChartData;
    },
    alarmChartData() {
      return this.$store.state.baseInfo.alarmChartData;
    },
    homeAlarmData() {
      return [
        { value: this.alarmChartData.slowQueryCount, name: this.$t('慢查询告警数'), type: 'alarm' },
        { value: this.alarmChartData.count, name: this.$t('总告警数'), type: 'alarm' },
      ];
    },
    // 告警情况图表配置
    homeAlertChartOption() {
      return alertChartOption(this.homeAlarmData, ['#F5876C', '#FFC685']);
    },
    appChartData() {
      return [
        { value: this.appChartInfo.idleAppCount, name: this.$t('闲置应用数'), type: 'app' },
        // { value: this.chartAppInfo.issueCount, name: this.$t('配置不当应用数') },
        { value: this.chartAppInfo.total, name: this.$t('总应用数'), type: 'app' },
      ];
    },
    // 应用情况图表配置
    appChartOption() {
      return alertChartOption(this.appChartData, ['#85CCA8', '#3E96C2']);
    },
    platformFeature() {
      return this.$store.state.platformFeature;
    },
    appDefaultLabel() {
      return this.appChartData.find((v) => v.value > 0) ?? this.appChartData[0];
    },
    alarmDefaultLabel() {
      return this.homeAlarmData.find((v) => v.value > 0) ?? this.homeAlarmData[0];
    },
  },
  watch: {
    homeAlarmData() {
      this.setChartFn('alarm');
    },
    // 应用
    appChartData() {
      this.setChartFn('app');
    },
  },
  created() {
    this.getAppsInfoCount();
  },
  mounted() {
    this.setChartFn('alarm');
    this.setChartFn('app');
    // 防抖
    window.addEventListener('resize', this.chartResize, false);
  },
  methods: {
    setChartFn(type) {
      if (type === 'app') {
        // 应用
        this.chartSet({
          id: 'chart-app-status',
          option: this.appChartOption,
          key: 'appChart',
          fn: (value) => {
            this.isAppLabel = value;
          },
        });
      } else {
        // 告警
        this.chartSet({
          id: 'alarm-status',
          option: this.homeAlertChartOption,
          key: 'alarmChart',
          fn: (value) => {
            this.isAlarmLabel = value;
          },
        });
      }
    },
    // 获取总应用数及issue_type应用数
    async getAppsInfoCount() {
      try {
        const res = await this.$store.dispatch('baseInfo/getAppsInfoCount');
        this.chartAppInfo = res;
        // 配置不当
        this.chartAppInfo.issueCount = res.issue_type_counts.find((v) => v.issue_type === 'misconfigured')?.count ?? 0;
        // 应用数
        this.$store.commit('baseInfo/updateAppChartData', {
          allCount: this.chartAppInfo.total,
        });
      } catch (e) {
        this.catchErrorHandler(e);
      }
    },
    toCreateApp() {
      this.$router.push({ name: 'createApp' });
    },
    // daysToSubtract 距离当前日期的指定天数
    getSpecifiedDate(daysToSubtract, currentDate = new Date()) {
      // 确保传入的一个 Date 对象
      if (!(currentDate instanceof Date)) {
        throw new Error('currentDate must be a Date object');
      }
      const resultDate = new Date(currentDate);
      // 减去指定的天数
      resultDate.setDate(resultDate.getDate() - daysToSubtract);
      return {
        start: formatDate(resultDate),
        end: formatDate(currentDate),
      };
    },
    handleDateChange(day) {
      // 通知首页需要时间接口数据更新
      this.curSelectionTime = this.getSpecifiedDate(day);
      bus.$emit('home-date', this.curSelectionTime);
    },
    chartResize() {
      this.alarmChart?.resize();
      this.appChart?.resize();
    },
    // 设置图表
    chartSet({ id, option, key, fn }) {
      this.$nextTick(() => {
        // 初始化
        const echart = echarts.init(document.getElementById(id));
        // 设置配置
        this[key] = echart;
        echart.setOption(option);
        echart.on('mouseover', () => {
          fn(false);
        });
        echart.on('mouseout', () => {
          fn(true);
        });
        echart.on('highlight', () => {
          fn(false);
        });
        echart.on('downplay', () => {
          fn(true);
        });
      });
    },
  },
};
</script>

<style lang="scss" scoped>
.home-top-title {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  margin-bottom: 12px;
  .title {
    font-weight: 700;
    font-size: 16px;
    color: #313238;
    .tips {
      font-size: 12px;
      font-weight: 400;
      color: #979ba5;
    }
  }
  .tools {
    display: flex;
    .date-select-cls {
      background: #fff;
      margin-right: 12px;
    }
  }
}
.app-overview-container {
  display: flex;
  .mr16 {
    margin-right: 16px;
  }
  .card-style {
    margin-right: 16px;
    &:last-child {
      margin-right: 0;
    }
  }
  .alarm-status,
  .app-status {
    position: relative;
    flex: 1;
    height: 200px;
    background: #fff;
    .chart-title {
      position: absolute;
      top: 12px;
      left: 24px;
    }
    .chart-el {
      height: 100%;
      width: 100%;
    }
    .default-text {
      transition: all 0.3s;
      position: absolute;
      flex-direction: column;
      left: calc(40% - 50px);
      top: calc(50% - 50px);
      height: 100px;
      width: 100px;
      background: transparent;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      .vlaue {
        font-size: 30px;
        font-weight: bold;
        color: #313238;
        line-height: 40px;
      }
      .name {
        color: #696b73;
        font-size: 12px;
      }
    }
  }
  .ops-dev-score {
    display: flex;
    flex-direction: column;
    width: 200px;
    height: 200px;
    padding: 12px 24px;
    background: #fff;
    .fraction {
      font-weight: 700;
      font-size: 48px;
      color: #313238;
    }
    .info {
      flex: 1;
      display: flex;
      align-items: center;
      justify-content: center;
      width: 100%;
      height: 100%;
    }
  }
  .card-title {
    font-weight: 700;
    font-size: 14px;
    color: #63656e;
    i {
      font-size: 14px;
      color: #dcdee5;
    }
  }
}
</style>
