<template>
  <div class="alarm-records-container">
    <bk-alert
      v-if="!!slowQueryCount"
      type="warning"
      :title="
        $t(
          '您有 {n} 条 MySQL 慢查询告警记录，请尽快处理，以确保应用正常运行。慢查询持续堆积会影响查询效率，严重时会导致应用无法访问。',
          { n: slowQueryCount }
        )
      "
    ></bk-alert>
    <div class="alarm-records">
      <bk-table
        :data="alarmRecords"
        size="small"
        :outer-border="false"
        :span-method="arraySpanMethod"
        :row-key="rowKey"
        :expand-row-keys="expandRowKeys"
        v-bkloading="{ isLoading: isLoading, zIndex: 10 }"
        row-class-name="record-table-row-cls"
        ext-cls="alarm-record-table-cls"
      >
        <bk-table-column
          type="expand"
          width="30"
        >
          <template slot-scope="props">
            <bk-table
              :data="props.row.alerts"
              :outer-border="false"
              :header-cell-style="{ background: 'red', borderRight: 'none' }"
              ext-cls="child-module-table-cls"
            >
              <bk-table-column
                label=""
                width="30"
              ></bk-table-column>
              <bk-table-column
                label=""
                width="240"
                show-overflow-tooltip
              >
                <template slot-scope="{ row: childRow }">
                  {{ childRow.alert_name }}
                </template>
              </bk-table-column>
              <bk-table-column
                label=""
                show-overflow-tooltip
              >
                <template slot-scope="{ row: childRow }">
                  {{ childRow.description }}
                </template>
              </bk-table-column>
              <bk-table-column
                label=""
                width="180"
                show-overflow-tooltip
              >
                <template slot-scope="{ row: childRow }">
                  {{ childRow?.start_time }}
                </template>
              </bk-table-column>
              <bk-table-column
                label=""
                width="140"
              >
                <template slot-scope="{ row: childRow }">
                  {{ calcDuration(childRow) }}
                </template>
              </bk-table-column>
              <bk-table-column
                label=""
                :width="localLanguage === 'en' ? 210 : 180"
              >
                <template slot-scope="{ row: childRow }">
                  <bk-button
                    :text="true"
                    @click="handleDetail(childRow)"
                  >
                    {{ $t('查看详情') }}
                  </bk-button>
                  <bk-button
                    v-if="childRow.labels && childRow.labels.includes('gcs_mysql_slow_query')"
                    :text="true"
                    class="ml10"
                    @click="handleSlowQuery(props.row, childRow)"
                  >
                    {{ $t('慢查询记录') }}
                  </bk-button>
                </template>
              </bk-table-column>
            </bk-table>
          </template>
        </bk-table-column>
        <bk-table-column
          :label="$t('告警名称')"
          width="240"
        >
          <template slot-scope="{ row }">
            <div
              class="app-name-wrapper"
              v-bk-overflow-tips="{ content: `${row.application.name}（${row.application.code}）` }"
            >
              <span
                class="click-area"
                @click="toAppDetail(row)"
              >
                <img
                  class="app-logo"
                  :src="row.application.logo_url"
                  alt="logo"
                />
                <span class="info">
                  {{ row.application.name }}
                  <span class="code">（{{ row.application.code }}）</span>
                </span>
              </span>
              <span class="ml20 msg">
                MySQL {{ $t('慢查询告警数量') }}:
                <span :class="{ 'slow-query': !!row.slow_query_count }">{{ row.slow_query_count }}</span>
                <span>/</span>
                <span>{{ row.count }}</span>
              </span>
            </div>
          </template>
        </bk-table-column>
        <bk-table-column
          :label="$t('告警内容')"
          prop="source"
          class-name="env-column-cls"
        ></bk-table-column>
        <bk-table-column
          :label="$t('告警开始时间')"
          width="180"
        ></bk-table-column>
        <bk-table-column
          :label="$t('持续时间')"
          width="140"
        ></bk-table-column>
        <bk-table-column
          :label="$t('操作')"
          width="180"
        ></bk-table-column>
      </bk-table>
    </div>
  </div>
</template>

<script>
import { formatDate, formatTime } from '@/common/tools';
import { bus } from '@/common/bus';
import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';
import 'dayjs/locale/zh-cn';
export default {
  name: 'HomeAlarmRecords',
  data() {
    return {
      alarmRecords: [],
      isLoading: false,
      formatTime,
      dayjs,
      relativeTime,
      expandRowKeys: [],
      slowQueryCount: 0,
      selectionTime: {},
      errorMessage: this.$t('GCS-MySQL 增强服务实例已解绑，无法再查看慢查询记录'),
    };
  },
  computed: {
    localLanguage() {
      return this.$store.state.localLanguage;
    },
  },
  created() {
    dayjs.extend(relativeTime);
    bus.$on('home-date', (time) => {
      this.selectionTime = time;
      this.queryAllAppAlerts();
    });
    // 默认值
    this.setDefaultDate();
    this.queryAllAppAlerts();
  },
  methods: {
    setDefaultDate() {
      const currentDate = new Date();
      // 减去1天
      const dateMinus1Day = new Date(currentDate);
      dateMinus1Day.setDate(currentDate.getDate() - 1);
      this.selectionTime = {
        end: formatDate(currentDate),
        start: formatDate(dateMinus1Day),
      };
    },
    // 查询用户各应用告警及数量
    async queryAllAppAlerts() {
      this.isLoading = true;
      try {
        const res = await this.$store.dispatch('alarm/queryAllAppAlerts', {
          data: {
            start_time: this.selectionTime.start,
            end_time: this.selectionTime.end,
          },
        });
        this.alarmRecords = res;

        const allCount = res.reduce((acc, item) => acc + item.count, 0);
        // 慢查询
        const allSlowQueryCount = res.reduce((acc, item) => acc + item.slow_query_count, 0);
        this.slowQueryCount = allSlowQueryCount;
        this.$store.commit('baseInfo/updateAlarmChartData', {
          slowQueryCount: allSlowQueryCount,
          count: allCount,
        });
        // 默认展开第一项
        if (res.length) {
          this.expandRowKeys.push(res[0].application.code);
        }
        this.$emit('async-list-length', {
          name: 'alarm',
          length: this.alarmRecords.length,
        });
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.isLoading = false;
        bus.$emit('on-close-loading');
      }
    },
    // 行key
    rowKey(row) {
      return row.application.code;
    },
    // 合并表格行
    arraySpanMethod({ columnIndex }) {
      if (columnIndex === 1) {
        return [1, 4];
      }
      if (columnIndex >= 3 && columnIndex <= 5) {
        return [0, 0];
      }
    },
    calcDuration(row) {
      const startTime = dayjs(row.start_time);
      const endDateStr = row.end_time || dayjs().format('YYYY-MM-DD HH:mm:ss');
      const endTime = dayjs(endDateStr);
      const differenceInMinutes = endTime.diff(startTime, 'minute');

      // 表示创当前时间减去差异
      const durationObj = dayjs().subtract(differenceInMinutes, 'minute');

      // 使用 fromNow(true) 方法显示相对时间
      return durationObj.fromNow(true);
    },
    // 应用详情
    toAppDetail(row) {
      this.$router.push({
        name: row.application.type === 'cloud_native' ? 'cloudAppSummary' : 'appSummary',
        params: { id: row.application.code },
      });
    },
    handleDetail(row) {
      window.open(row.detail_link, '_blank');
    },
    // 处理慢查询页面跳转
    handleSlowQuery(row, childRow) {
      const params = {
        appCode: row.application.code,
        moduleId: childRow?.module_name || 'default',
      };
      this.getServiceInfo(params, childRow.env);
    },
    async getServiceInfo(params, env) {
      try {
        const GCS_MYSQL_NAME = 'gcs_mysql';
        const res = await this.$store.dispatch('service/getServiceInfo', params);
        const services = res[env];
        if (!services.length) {
          this.$paasMessage({
            theme: 'error',
            message: this.errorMessage,
          });
          return;
        }
        // 服务服务id
        const serviceId = services?.find((v) => v.name === GCS_MYSQL_NAME)?.service_id;
        this.getServiceInstances(params, serviceId);
      } catch (e) {
        this.catchErrorHandler(e);
      }
    },
    // 获取服务实例详情
    async getServiceInstances(params, serviceId) {
      try {
        const res = await this.$store.dispatch('service/getServiceInstances', {
          ...params,
          service: serviceId,
        });
        if (!res.results.length) {
          this.$paasMessage({
            theme: 'error',
            message: this.errorMessage,
          });
          return;
        }
        const url = `${res.results[0].service_instance?.config?.admin_url}&redirect_url=instance.slow_sql.fingers.list`;
        window.open(url, '_blank');
      } catch (e) {
        this.catchErrorHandler(e);
      }
    },
  },
};
</script>

<style lang="scss" scoped>
.alarm-records-container {
  .alarm-records {
    margin-top: 12px;

    .app-name-wrapper {
      color: #313238;
      .click-area {
        cursor: pointer;
      }
      .app-logo {
        width: 16px;
        height: 16px;
        margin-right: 8px;
        vertical-align: middle;
      }
      .code {
        color: #979ba5;
      }
      .info:hover {
        color: #3a84ff;
      }
      .msg {
        color: #63656e;
      }
      .slow-query {
        color: #ea3636;
      }
    }
  }
  :deep(.alarm-record-table-cls) .bk-table-body td.bk-table-expanded-cell {
    padding: 0px !important;
  }
  :deep(.alarm-record-table-cls) {
    .bk-table-body {
      width: 100% !important;
    }
    .bk-table-body-wrapper .record-table-row-cls {
      background: #f0f1f5;
    }
    tr.expanded .bk-table-expand-icon .bk-icon {
      color: #63656e;
    }
    .bk-table-expand-icon .bk-icon {
      color: #979ba5;
    }
    .child-module-table-cls {
      .bk-table-header-wrapper {
        display: none;
      }
      .bk-table-body-wrapper {
        color: #63656e;
      }
    }
    .env-column-cls .cell {
      display: flex;
      align-items: center;
      .bk-tooltip {
        position: absolute;
        right: 16px;
      }
    }
  }
}
.mr4 {
  margin-right: 4px;
}
</style>
