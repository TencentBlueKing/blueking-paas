<template>
  <div>
    <section class="home-top-title">
      <div class="title">
        {{ $t('应用总览') }}
      </div>
      <div class="tools">
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
        class="alarm-status card-style chart-box"
        v-if="platformFeature.MONITORING"
      >
        <div class="card-title chart-title">
          {{ $t('告警情况') }}
        </div>
        <chart
          style="width: 450px; height: 200px"
          id="alarm-status"
          class="chart-el"
        ></chart>
        <div
          class="default-text"
          v-if="isAlarmLabel"
        >
          <p :class="['vlaue', { high: alarmDefaultLabel.colorType === 'high' }]">{{ alarmDefaultLabel.value }}</p>
          <p class="name">{{ alarmDefaultLabel.name }}</p>
        </div>
        <div class="date-change-box">
          <bk-select
            v-model="curDate"
            style="width: 85px"
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
        </div>
        <!-- <div
          class="chart-el chart-alert"
          v-charts="alertChartOption"
        ></div> -->
      </div>
      <!-- 应用情况 -->
      <div class="app-status card-style chart-box">
        <div class="card-title chart-title">
          {{ $t('应用情况') }}
          <i
            class="paasng-icon paasng-info-line"
            v-bk-tooltips="{
              content: $t('更新于 {t}之前', { t: appChartInfo.updateTime }),
              theme: 'light',
            }"
          ></i>
        </div>
        <chart
          style="width: 450px; height: 200px"
          id="chart-app-status"
          class="chart-el"
        ></chart>
        <div
          class="default-text"
          v-if="isAppLabel"
        >
          <p :class="['vlaue', { high: appDefaultLabel.colorType === 'high' }]">{{ appDefaultLabel.value }}</p>
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
        { label: `1 ${this.$t('天')}`, id: 1 },
        { label: `7 ${this.$t('天')}`, id: 7 },
        { label: `15 ${this.$t('天')}`, id: 15 },
        { label: `1 ${this.$t('个月')}`, id: 30 },
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
      const totalCount = this.alarmChartData.count;
      const slowQueryCount = this.alarmChartData.slowQueryCount;
      const data = [
        {
          value: slowQueryCount,
          name: this.$t('慢查询告警数'),
          type: 'alarm',
          colorType: 'high',
          color: '#F5876C',
        },
        {
          value: totalCount - slowQueryCount,
          name: totalCount === 0 || slowQueryCount === 0 ? this.$t('总告警数') : this.$t('其他告警数'),
          type: 'alarm',
          colorType: 'low',
          color: '#FFC685',
        },
      ];
      if (data.find((v) => v.colorType === 'high' && v.value === 0)) {
        return data.filter((v) => v.colorType === 'low');
      }
      return data;
    },
    // 告警情况图表配置
    homeAlertChartOption() {
      const colors = this.homeAlarmData.map((v) => v.color);
      return alertChartOption(this.homeAlarmData, colors);
    },
    appChartData() {
      const totalAppCount = this.chartAppInfo.total;
      const idleAppCount = this.appChartInfo.idleAppCount;
      const data = [
        {
          value: idleAppCount,
          name: this.$t('闲置应用数'),
          type: 'app',
          colorType: 'high',
          color: '#FFA66B',
        },
        {
          value: totalAppCount - idleAppCount,
          name: totalAppCount === 0 || idleAppCount === 0 ? this.$t('总应用数') : this.$t('活跃应用数'),
          type: 'app',
          colorType: 'low',
          color: '#3E96C2',
        },
      ];
      if (data.find((v) => v.colorType === 'high' && v.value === 0)) {
        return data.filter((v) => v.colorType === 'low');
      }
      return data;
    },
    // 应用情况图表配置
    appChartOption() {
      const colors = this.appChartData.map((v) => v.color);
      return alertChartOption(this.appChartData, colors);
    },
    platformFeature() {
      return this.$store.state.platformFeature;
    },
    appDefaultLabel() {
      return this.appChartData.find((v) => v.value > 0) ?? this.appChartData[0];
    },
    alarmDefaultLabel() {
      if (this.homeAlarmData.length > 1) {
        return this.homeAlarmData.find((v) => v.value > 0) ?? this.homeAlarmData[1];
      }
      return this.homeAlarmData[0];
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
  .chart-box {
    display: flex;
    justify-content: center;
    .date-change-box {
      position: absolute;
      top: 12px;
      right: 12px;
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
      left: calc(50% - 95px);
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
        &.high {
          color: #ea3636;
        }
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
