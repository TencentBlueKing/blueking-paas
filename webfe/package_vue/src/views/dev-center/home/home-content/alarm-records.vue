<template>
  <div class="alarm-records-container">
    <bk-alert
      v-if="!!slowQueryCount"
      type="warning"
      :title="
        $t(
          '您有 {n} 条慢查询告警记录，请尽快处理，以确保应用正常运行。慢查询持续堆积会影响查询效率，严重时会导致应用无法访问。',
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
                width="180"
              >
                <template slot-scope="{ row: childRow }">
                  <bk-button
                    :text="true"
                    class="ml10"
                    @click="handleDetail(childRow)"
                  >
                    {{ $t('查看详情') }}
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
              {{ $t('慢查询告警数量') }}: <span class="slow-query">{{ row.slow_query_count }}</span>/{{ row.count }}
            </div>
          </template>
        </bk-table-column>
        <bk-table-column
          :label="$t('告警内容')"
          prop="source"
          class-name="env-column-cls"
        >
          <template slot-scope="{ row }">
            <bk-popover
              :ref="`quit${row.application.code}`"
              placement="top"
              theme="light-border"
              trigger="click"
              width="260"
              :on-hide="handleHide"
              ext-cls="exit-app-popover-cls"
            >
              <bk-button
                :theme="'default'"
                type="submit"
                size="small"
                ext-cls="exit-app-button"
                @click="handleLeaveApp(row)"
              >
                {{ $t('退出应用') }}
              </bk-button>
              <div slot="content">
                <div class="popover-title">{{ $t('退出应用') }}</div>
                <div class="popover-content">{{ $t('退出并放弃此应用的对应权限，是否确定？') }}</div>
                <div class="popover-operate">
                  <bk-button
                    :theme="'primary'"
                    size="small"
                    class="mr4"
                    :loading="isPopoverLoading"
                    @click="confirmLeaveApp(`quit${row.application.code}`)"
                  >
                    {{ $t('确定') }}
                  </bk-button>
                  <bk-button
                    :theme="'default'"
                    size="small"
                    @click="handleCancel(`quit${row.application.code}`)"
                  >
                    {{ $t('取消') }}
                  </bk-button>
                </div>
              </div>
            </bk-popover>
          </template>
        </bk-table-column>
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
      isPopoverLoading: false,
      exitAppDataCode: '',
      selectionTime: {},
    };
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
    // 退出应用
    async handleLeaveApp(data) {
      this.exitAppDataCode = data.application.code;
    },
    // 确定退出应用
    async confirmLeaveApp(refName) {
      this.isPopoverLoading = true;
      try {
        await this.$store.dispatch('member/quitApplication', {
          appCode: this.exitAppDataCode,
        });
        this.handleCancel(refName);
        this.$paasMessage({
          theme: 'success',
          message: this.$t('退出成功'),
        });
        // 重新刷新表格
        this.queryAllAppAlerts();
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: `${this.$t('退出应用失败：')} ${e.detail}`,
        });
      } finally {
        this.isPopoverLoading = false;
      }
    },
    // 取消关闭
    handleCancel(refName) {
      this.$refs[refName].hideHandler();
    },
    handleHide() {
      this.isPopoverLoading = false;
    },
    handleDetail(row) {
      window.open(row.detail_link, '_blank');
    },
  },
};
</script>

<style lang="scss" scoped>
.alarm-records-container {
  .alarm-records {
    margin-top: 12px;

    .app-name-wrapper {
      cursor: pointer;
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
      .slow-query {
        color: #EA3636;
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
    .child-module-table-cls .bk-table-header-wrapper {
      display: none;
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
.exit-app-popover-cls {
  .popover-title {
    font-size: 14px;
    color: #313238;
    margin-bottom: 10px;
  }
  .popover-content {
    margin-bottom: 10px;
  }
  .popover-operate {
    text-align: right;
  }
  .tl em {
    font-weight: bold;
  }
}
</style>
