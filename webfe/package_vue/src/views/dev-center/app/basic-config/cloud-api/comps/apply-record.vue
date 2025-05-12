<template>
  <div class="paasng-api-panel">
    <div class="search-wrapper">
      <div class="left flex-row">
        <section class="search-item">
          <div class="label mr15">
            {{ $t('申请时间') }}
          </div>
          <div class="date-wrapper">
            <bk-date-picker
              v-model="initDateTimeRange"
              ext-cls="application-time"
              style="width: 200px"
              :placeholder="$t('选择日期范围')"
              :type="'daterange'"
              :shortcuts="shortcuts"
              :shortcut-close="true"
              :options="dateOptions"
              @change="handleDateChange"
            />
          </div>
        </section>
        <div class="flex-row align-items-center">
          <div class="label mr15">{{ $t('类型') }}</div>
          <bk-select
            v-model="typeValue"
            style="width: 200px"
            :clearable="false"
            @change="handleSelect"
          >
            <bk-option
              v-for="option in typeList"
              :key="option.id"
              :id="option.id"
              :name="option.name"
            ></bk-option>
          </bk-select>
        </div>
      </div>
      <div class="right-wrapper flex-row">
        <bk-search-select
          style="width: 100%"
          v-model="searchSelectValue"
          :data="searchSelectData"
          :placeholder="$t('搜索网关名称/申请人')"
          :clearable="true"
          :show-condition="false"
          :remote-method="handleRemoteMethod"
          :remote-empty-text="Object.keys(searchData).length ? $t('无匹配人员') : $t('请输入申请人')"
        />
      </div>
    </div>
    <paas-content-loader
      :is-loading="loading"
      :offset-top="0"
      placeholder="cloud-api-inner-loading"
      :height="300"
    >
      <div>
        <bk-table
          :data="tableList"
          ref="tableRef"
          size="small"
          :empty-text="$t('暂无数据')"
          :pagination="pagination"
          :show-pagination-info="true"
          :header-border="false"
          :outer-border="false"
          @page-change="pageChange"
          @page-limit-change="limitChange"
          @filter-change="handleFilterChange"
        >
          <div slot="empty">
            <table-empty
              :keyword="tableEmptyConf.keyword"
              :abnormal="tableEmptyConf.isAbnormal"
              @reacquire="fetchList"
              @clear-filter="clearFilterKey"
            />
          </div>
          <bk-table-column
            :label="$t('申请人')"
            :render-header="$renderHeader"
          >
            <template slot-scope="{ row }">
              <bk-user-display-name
                v-if="platformFeature.MULTI_TENANT_MODE"
                :user-id="row.applied_by"
              ></bk-user-display-name>
              <span v-else>{{ row.applied_by }}</span>
            </template>
          </bk-table-column>
          <bk-table-column
            prop="applied_time"
            :label="$t('申请时间')"
            :show-overflow-tooltip="true"
            :render-header="$renderHeader"
          />
          <bk-table-column
            :label="$t('API类型')"
            :render-header="$renderHeader"
          >
            <template slot-scope="props">
              {{ typeMap[props.row.type] }}
            </template>
          </bk-table-column>
          <bk-table-column :label="isComponentApi ? $t('系统') : $t('网关')">
            <template slot-scope="props">
              <template v-if="isComponentApi">
                {{ props.row.system_name }}
                <template v-if="!!props.row.tag">
                  <span
                    :class="[
                      { inner: [$t('内部版'), $t('互娱外部版')].includes(props.row.tag) },
                      { clound: [$t('上云版'), $t('互娱外部上云版')].includes(props.row.tag) },
                    ]"
                  >
                    {{ props.row.tag }}
                  </span>
                </template>
              </template>
              <template v-else>
                {{ props.row.api_name }}
              </template>
            </template>
          </bk-table-column>
          <bk-table-column
            :label="$t('审批人')"
            :render-header="$renderHeader"
            :show-overflow-tooltip="true"
          >
            <template slot-scope="{ row }">
              <template v-if="!row.handled_by.length">--</template>
              <span v-else>
                <template v-if="platformFeature.MULTI_TENANT_MODE">
                  <span
                    v-for="userId in row.handled_by"
                    :key="userId"
                  >
                    <bk-user-display-name :user-id="userId"></bk-user-display-name>
                    <span>，</span>
                  </span>
                </template>
                <template>{{ getHandleBy(row.handled_by) }}</template>
              </span>
            </template>
          </bk-table-column>
          <bk-table-column
            :label="$t('审批状态')"
            :render-header="$renderHeader"
            prop="apply_status"
            column-key="apply_status"
            :filters="statusFilters"
            :filter-multiple="false"
          >
            <template slot-scope="props">
              <template v-if="props.row.apply_status === 'approved'">
                <span class="paasng-icon paasng-pass" />
                {{ getStatusDisplay(props.row.apply_status) }}
              </template>
              <template v-else-if="props.row.apply_status === 'partial_approved'">
                {{ getStatusDisplay(props.row.apply_status) }}
              </template>
              <template v-else-if="props.row.apply_status === 'rejected'">
                <span class="paasng-icon paasng-reject" />
                {{ getStatusDisplay(props.row.apply_status) }}
              </template>
              <template v-else>
                <round-loading ext-cls="applying" />
                {{ getStatusDisplay(props.row.apply_status) }}
              </template>
            </template>
          </bk-table-column>
          <bk-table-column
            :label="$t('审批时间')"
            :render-header="$renderHeader"
          >
            <template slot-scope="props">
              {{ props.row.handled_time || '--' }}
            </template>
          </bk-table-column>
          <bk-table-column
            :label="$t('操作')"
            width="100"
          >
            <template slot-scope="props">
              <div class="table-operate-buttons">
                <bk-button
                  theme="primary"
                  size="small"
                  text
                  @click="handleOpenDetail(props.row)"
                >
                  {{ $t('详情') }}
                </bk-button>
              </div>
            </template>
          </bk-table-column>
        </bk-table>
      </div>
    </paas-content-loader>

    <bk-sideslider
      quick-close
      :title="sliderTitle"
      :width="600"
      :is-show.sync="detailSliderConf.show"
    >
      <div
        slot="content"
        v-bkloading="{ isLoading: detailLoading }"
        class="slider-detail-content"
      >
        <section
          v-if="!detailLoading"
          class="paasng-kv-list"
        >
          <div class="item">
            <div class="key">{{ $t('申请人') }}：</div>
            <div class="value">
              {{ curRecord.applied_by }}
            </div>
          </div>
          <div
            v-if="!isComponentApi"
            class="item"
          >
            <div class="key">
              {{ $t('授权维度：') }}
            </div>
            <div class="value">
              {{ curRecord.grant_dimension === 'resource' ? $t('按资源') : $t('按网关') }}
            </div>
          </div>
          <div class="item">
            <div class="key">
              {{ $t('有效时间：') }}
            </div>
            <div class="value">
              {{ curRecord.expire_days === 0 ? $t('永久') : Math.ceil(curRecord.expire_days / 30) + $t('个月') }}
            </div>
          </div>
          <div class="item">
            <div class="key">
              {{ $t('申请理由：') }}
            </div>
            <div class="value">
              {{ curRecord.reason || '--' }}
            </div>
          </div>
          <div class="item">
            <div class="key">
              {{ $t('申请时间：') }}
            </div>
            <div class="value">
              {{ curRecord.applied_time }}
            </div>
          </div>
          <div class="item">
            <div class="key">
              {{ $t('审批人：') }}
            </div>
            <div class="value">
              {{ getHandleBy(curRecord.handled_by) || '--' }}
            </div>
          </div>
          <div class="item">
            <div class="key">
              {{ $t('审批时间：') }}
            </div>
            <div class="value">
              {{ curRecord.handled_time || '--' }}
            </div>
          </div>
          <div class="item">
            <div class="key">
              {{ $t('审批状态：') }}
            </div>
            <div class="value">
              {{ $t(curRecord.apply_status_display) || '--' }}
            </div>
          </div>
          <div class="item">
            <div class="key">
              {{ $t('审批内容：') }}
            </div>
            <div
              class="value"
              style="line-height: 22px; padding-top: 10px"
            >
              {{ curRecord.comment || '--' }}
            </div>
          </div>
          <div class="item">
            <div class="key">
              {{ isComponentApi ? $t('系统名称：') : $t('网关名称：') }}
            </div>
            <div class="value">
              {{ (isComponentApi ? curRecord.system_name : curRecord.api_name) || '--' }}
            </div>
          </div>
          <div
            v-if="isComponentApi"
            class="item"
          >
            <div class="key">
              {{ $t('API列表：') }}
            </div>
            <div
              class="value"
              style="line-height: 22px; padding-top: 10px"
            >
              <bk-table
                :size="'small'"
                :data="curRecord.components"
                :header-cell-style="{ background: '#fafbfd', borderRight: 'none' }"
                ext-cls="paasng-expand-table"
              >
                <div slot="empty">
                  <table-empty empty />
                </div>
                <bk-table-column
                  prop="name"
                  :label="$t('API名称')"
                />
                <bk-table-column
                  prop="method"
                  :label="$t('审批状态')"
                >
                  <template slot-scope="prop">
                    <template v-if="prop.row['apply_status'] === 'rejected'">
                      <span class="paasng-icon paasng-reject" />
                      {{ $t('驳回') }}
                    </template>
                    <template v-else-if="prop.row['apply_status'] === 'pending'">
                      <round-loading ext-cls="applying" />
                      {{ $t('待审批') }}
                    </template>
                    <template v-else>
                      <span class="paasng-icon paasng-pass" />
                      {{ prop.row['apply_status'] === 'approved' ? $t('通过') : $t('部分通过') }}
                    </template>
                  </template>
                </bk-table-column>
              </bk-table>
            </div>
          </div>
          <div
            v-else
            class="item"
          >
            <div class="key">
              {{ $t('API列表：') }}
            </div>
            <div
              v-if="curRecord.grant_dimension === 'resource'"
              class="value"
              style="line-height: 22px; padding-top: 10px"
            >
              <bk-table
                :size="'small'"
                :data="curRecord.resources"
                :header-cell-style="{ background: '#fafbfd', borderRight: 'none' }"
                ext-cls="paasng-expand-table"
              >
                <div slot="empty">
                  <table-empty empty />
                </div>
                <bk-table-column
                  prop="name"
                  :label="$t('API名称')"
                />
                <bk-table-column
                  prop="method"
                  :label="$t('审批状态')"
                >
                  <template slot-scope="prop">
                    <template v-if="prop.row['apply_status'] === 'rejected'">
                      <span class="paasng-icon paasng-reject" />
                      {{ $t('驳回') }}
                    </template>
                    <template v-else-if="prop.row['apply_status'] === 'pending'">
                      <round-loading ext-cls="applying" />
                      {{ $t('待审批') }}
                    </template>
                    <template v-else>
                      <span class="paasng-icon paasng-pass" />
                      {{ prop.row['apply_status'] === 'approved' ? $t('通过') : $t('部分通过') }}
                    </template>
                  </template>
                </bk-table-column>
              </bk-table>
            </div>
            <div
              v-else
              class="value"
            >
              {{ $t('网关下所有资源') }}
            </div>
          </div>
        </section>
      </div>
    </bk-sideslider>
  </div>
</template>

<script>
import moment from 'moment';
import { mapState, mapGetters } from 'vuex';

export default {
  props: {
    typeList: {
      type: Array,
      default: () => [],
    },
  },
  data() {
    return {
      loading: false,
      tableList: [],
      pagination: {
        current: 1,
        limit: 10,
        count: 0,
      },
      currentBackup: 1,
      typeMap: {
        component: this.$t('组件API'),
        gateway: this.$t('网关API'),
      },
      typeValue: 'gateway',
      levelMap: {
        normal: this.$t('普通'),
        special: this.$t('特殊'),
        sensitive: this.$t('敏感'),
        unlimited: this.$t('无限制'),
      },
      detailLoading: false,
      detailSliderConf: {
        title: '',
        show: false,
      },
      curRecord: {
        applied_by: '',
        applied_time: '',
        handled_by: [],
        handled_time: '',
        system_name: '',
        comment: '',
        components: [],
        resources: [],
        expire_days: 0,
        reason: '',
        grant_dimension: '',
      },
      statusList: [
        { id: 'approved', name: this.$t('全部通过') },
        { id: 'partial_approved', name: this.$t('部分通过') },
        { id: 'rejected', name: this.$t('已驳回') },
        { id: 'pending', name: this.$t('待审批') },
      ],
      statusValue: '',
      initDateTimeRange: [],
      daterange: [new Date(), new Date()],
      shortcuts: [
        {
          text: this.$t('今天'),
          value() {
            const end = new Date();
            const start = new Date();
            return [start, end];
          },
        },
        {
          text: this.$t('最近7天'),
          value() {
            const end = new Date();
            const start = new Date();
            start.setTime(start.getTime() - 3600 * 1000 * 24 * 7);
            return [start, end];
          },
        },
        {
          text: this.$t('最近30天'),
          value() {
            const end = new Date();
            const start = new Date();
            start.setTime(start.getTime() - 3600 * 1000 * 24 * 30);
            return [start, end];
          },
        },
        {
          text: this.$t('最近半年'),
          value() {
            const end = new Date();
            const start = new Date();
            start.setTime(start.getTime() - 3600 * 1000 * 24 * 180);
            return [start, end];
          },
        },
      ],
      dateOptions: {
        // 大于今天的都不能选
        disabledDate(date) {
          return date && date.valueOf() > Date.now() - 86400;
        },
      },
      dateRange: {
        startTime: '',
        endTime: '',
      },
      tableEmptyConf: {
        keyword: '',
        isAbnormal: false,
      },
      searchSelectValue: [],
      searchData: {},
    };
  },
  computed: {
    ...mapState(['localLanguage', 'platformFeature']),
    ...mapGetters(['tenantId']),
    isComponentApi() {
      return this.typeValue === 'component';
    },
    appCode() {
      return this.$route.params.id;
    },
    curDispatchMethod() {
      return this.typeValue === 'component' ? 'getSysApplyRecords' : 'getApplyRecords';
    },
    curDetailDispatchMethod() {
      return this.typeValue === 'component' ? 'getSysApplyRecordDetail' : 'getApplyRecordDetail';
    },
    sliderTitle() {
      return this.isComponentApi ? this.$t('申请组件API单据详情') : this.$t('申请网关API单据详情');
    },
    statusFilters() {
      return this.statusList.map((v) => {
        return {
          text: v.name,
          value: v.id,
        };
      });
    },
    searchSelectData() {
      const isTenantMode = this.platformFeature.MULTI_TENANT_MODE || false;
      return [
        {
          name: this.isComponentApi ? this.$t('系统名称') : this.$t('网关名称'),
          id: 'keyword',
          placeholder: this.isComponentApi ? this.$t('请输入系统名称') : this.$t('请输入网关名'),
          children: [],
        },
        {
          name: this.$t('申请人'),
          id: 'applied_by',
          placeholder: this.$t('请输入申请人'),
          remote: isTenantMode,
          async: isTenantMode,
          children: [],
        },
      ];
    },
  },
  watch: {
    $route() {
      const end = new Date();
      const start = new Date();
      start.setTime(start.getTime() - 3600 * 1000 * 24 * 7);
      this.initDateTimeRange = [start, end];
      this.dateRange.startTime = moment(start).format('YYYY-MM-DD');
      this.dateRange.endTime = moment(end).format('YYYY-MM-DD');
      this.dateRange.startTime = `${this.dateRange.startTime} 00:00:00`;
      this.dateRange.endTime = `${this.dateRange.endTime} 23:59:59`;
      this.init();
    },
    'pagination.current'(value) {
      this.currentBackup = value;
    },
    searchSelectValue(newVal) {
      this.searchData = newVal.length ? Object.fromEntries(newVal.map((v) => [v.id, v.values[0].id])) : {};
      this.resetPagination();
      this.fetchList();
    },
  },
  created() {
    moment.locale(this.localLanguage);
    window.moment = moment;
    this.isFilter = false;
  },
  mounted() {
    const end = new Date();
    const start = new Date();
    start.setTime(start.getTime() - 3600 * 1000 * 24 * 7);
    this.initDateTimeRange = [start, end];
    this.dateRange.startTime = moment(start).format('YYYY-MM-DD');
    this.dateRange.endTime = moment(end).format('YYYY-MM-DD');
    this.dateRange.startTime = `${this.dateRange.startTime} 00:00:00`;
    this.dateRange.endTime = `${this.dateRange.endTime} 23:59:59`;
    this.init();
  },
  methods: {
    resetPagination() {
      this.pagination = Object.assign(
        {},
        {
          current: 1,
          limit: 10,
          count: 0,
        }
      );
    },

    getStatusDisplay(payload) {
      const data = this.statusList.find((item) => item.id === payload);
      if (data) {
        return data.name;
      }
      return '--';
    },

    handleDateChange(date, type) {
      this.dateRange = {
        startTime: `${date[0]} 00:00:00`,
        endTime: `${date[1]} 23:59:59`,
      };
      this.resetPagination();
      this.fetchList();
    },

    handleSelect(value, option) {
      this.resetPagination();
      this.fetchList();
    },

    getHandleBy(payload) {
      const list = payload.filter((item) => !!item);
      if (list.length < 1) {
        return '--';
      }
      return list.join('，');
    },

    pageChange(page) {
      if (this.currentBackup === page) {
        return;
      }
      this.pagination.current = page;
      this.fetchList();
    },

    limitChange(currentLimit, prevLimit) {
      this.pagination.limit = currentLimit;
      this.pagination.current = 1;
      this.fetchList();
    },

    // 表头过滤
    handleFilterChange(filds) {
      if (filds.apply_status) {
        this.statusValue = filds.apply_status.length ? filds.apply_status[0] : '';
      }
      this.resetPagination();
      this.fetchList();
    },

    init() {
      this.fetchList();
    },

    async fetchList() {
      this.loading = true;
      const params = {
        limit: this.pagination.limit,
        offset: this.pagination.limit * (this.pagination.current - 1),
        appCode: this.appCode,
        applied_by: this.searchData['applied_by'] || '',
        apply_status: this.statusValue,
        applied_time_start: new Date(this.dateRange.startTime).getTime() / 1000,
        applied_time_end: new Date(this.dateRange.endTime).getTime() / 1000,
        query: this.searchData['keyword'] || '',
      };
      try {
        const res = await this.$store.dispatch(`cloudApi/${this.curDispatchMethod}`, params);
        (res.data.results || []).forEach((item) => {
          item.type = this.typeValue;
        });
        this.pagination.count = res.data.count;
        this.tableList = res.data.results;
        this.updateTableEmptyConfig();
        this.tableEmptyConf.isAbnormal = false;
      } catch (e) {
        this.tableEmptyConf.isAbnormal = true;
        this.catchErrorHandler(e);
      } finally {
        this.loading = false;
      }
    },

    async handleOpenDetail({ id }) {
      this.detailSliderConf.show = true;
      this.detailLoading = true;
      try {
        const res = await this.$store.dispatch(`cloudApi/${this.curDetailDispatchMethod}`, {
          appCode: this.appCode,
          recordId: id,
        });
        this.curRecord = Object.assign(this.curRecord, res.data);
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.detailLoading = false;
      }
    },

    clearFilterKey() {
      this.statusValue = '';
      this.searchSelectValue = [];
      this.$refs.tableRef.clearFilter();
      this.resetPagination();
    },

    updateTableEmptyConfig() {
      if (this.searchSelectValue.length || this.statusValue) {
        this.tableEmptyConf.keyword = 'placeholder';
        return;
      }
      // 恒定条件不展示清空交互
      this.tableEmptyConf.keyword = '$CONSTANT';
    },
    handleRemoteMethod(val) {
      return new Promise(async (resolve) => {
        if (val.includes(this.$t('申请人'))) {
          resolve([]);
          return;
        }
        const users = await this.getTenantUsers(val);
        resolve(users);
      });
    },
    // 获取多租户人员数据
    async getTenantUsers(keyword) {
      if (!this.tenantId) return [];
      try {
        const { data = [] } = await this.$store.dispatch('tenant/searchTenantUsers', {
          keyword,
          tenantId: this.tenantId,
        });
        return data.map(({ login_name, bk_username, ...rest }) => ({
          ...rest,
          name: login_name,
          id: bk_username,
        }));
      } catch {
        return [];
      }
    },
  },
};
</script>

<style lang="scss" scoped>
.search-wrapper {
  display: flex;
  flex-wrap: nowrap;
  gap: 12px;
  justify-content: space-between;
  margin-bottom: 16px;
  .record-type-cls {
    width: auto;
  }
  .left {
    flex-shrink: 0;
    gap: 12px;
  }
  .right-wrapper {
    flex: 1;
    max-width: 420px;
  }
  .search-item {
    display: inline-block;
    vertical-align: middle;
  }
  .label,
  .member-wrapper,
  .date-wrapper,
  .select-wrapper {
    display: inline-block;
    vertical-align: top;
  }
  .label {
    line-height: 32px;
  }
  .select-wrapper {
    width: 98px;
    &.en {
      width: 130px;
    }
  }
}

.table-operate-buttons {
  position: relative;
  left: -12px;
}

span.sensitive {
  color: #ff0000;
}

span.inner {
  color: rgb(58, 171, 255);
  opacity: 0.7;
}

span.clound {
  color: #45e35f;
}

span.paasng-pass {
  position: relative;
  top: 1px;
  color: #2dcb56;
  font-size: 14px;
}

span.paasng-reject {
  position: relative;
  top: 1px;
  color: #ea3636;
  font-size: 14px;
}

.applying {
  position: relative;
  top: -1px;
}

.slider-detail-content {
  padding: 30px;
  min-height: calc(100vh - 50px);
}

.paasng-kv-list {
  border: 1px solid #f0f1f5;
  border-radius: 2px;
  background: #fafbfd;
  padding: 10px 20px;

  .item {
    display: flex;
    font-size: 14px;
    border-bottom: 1px dashed #dcdee5;
    min-height: 40px;
    line-height: 40px;

    &:last-child {
      border-bottom: none;
    }

    .key {
      min-width: 105px;
      padding-right: 24px;
      color: #63656e;
      text-align: right;
    }

    .value {
      color: #313238;
      flex: 1;
    }
  }
}

.bk-table .paasng-expand-table {
  tr {
    background-color: #fafbfd;
  }

  td,
  th {
    padding: 0 !important;
    height: 42px !important;
    cursor: default !important;
  }
}

/deep/ .application-time .bk-date-picker-rel .bk-date-picker-editor {
  padding: 0 40px 0 10px;
}
</style>
