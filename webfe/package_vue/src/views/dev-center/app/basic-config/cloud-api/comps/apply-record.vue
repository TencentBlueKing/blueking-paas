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
          :placeholder="searchPlaceholder"
          :clearable="true"
          :show-condition="false"
          :remote-method="handleRemoteMethod"
          :remote-empty-text="Object.keys(searchData).length ? $t('无匹配人员') : $t('请输入申请人')"
          :key="typeValue"
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
          :key="typeValue"
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
            v-if="!isMcpService"
          >
            <template slot-scope="{ row }">
              {{ typeMap[row.type] }}
            </template>
          </bk-table-column>
          <bk-table-column :label="getTypeLabel()">
            <template slot-scope="{ row }">
              <template v-if="row.type === 'mcp'">
                {{ row.mcp_server?.name }}
              </template>
              <template v-else-if="isComponentApi">
                {{ row.system_name }}
                <template v-if="!!row.tag">
                  <span
                    :class="[
                      { inner: [$t('内部版'), $t('互娱外部版')].includes(row.tag) },
                      { clound: [$t('上云版'), $t('互娱外部上云版')].includes(row.tag) },
                    ]"
                  >
                    {{ row.tag }}
                  </span>
                </template>
              </template>
              <template v-else>
                {{ row.api_name }}
              </template>
            </template>
          </bk-table-column>
          <bk-table-column
            :label="$t('审批人')"
            :render-header="$renderHeader"
            :show-overflow-tooltip="true"
          >
            <template slot-scope="{ row }">
              <template v-if="platformFeature.MULTI_TENANT_MODE">
                <span
                  v-for="userId in row.handled_by"
                  :key="userId"
                >
                  <bk-user-display-name :user-id="userId"></bk-user-display-name>
                  <span>，</span>
                </span>
              </template>
              <template v-else>{{ getHandleBy(row.handled_by) }}</template>
            </template>
          </bk-table-column>
          <bk-table-column
            :label="$t('审批状态')"
            :render-header="$renderHeader"
            prop="apply_status"
            column-key="apply_status"
            :filters="statusFilters"
            :filter-multiple="false"
            :key="typeValue"
          >
            <template slot-scope="{ row }">
              <span
                v-if="['approved', 'rejected'].includes(row.apply_status)"
                :class="[
                  'paasng-icon',
                  {
                    'paasng-pass': row.apply_status === 'approved',
                    'paasng-reject': row.apply_status === 'rejected',
                  },
                ]"
              />
              <round-loading
                v-else-if="row.apply_status === 'pending'"
                ext-cls="applying"
              />
              {{ getStatusDisplay(row.apply_status) }}
            </template>
          </bk-table-column>
          <bk-table-column
            :label="$t('审批时间')"
            :render-header="$renderHeader"
          >
            <template slot-scope="{ row }">
              {{ row.handled_time || '--' }}
            </template>
          </bk-table-column>
          <bk-table-column
            :label="$t('操作')"
            width="100"
          >
            <template slot-scope="{ row }">
              <div class="table-operate-buttons">
                <bk-button
                  theme="primary"
                  size="small"
                  text
                  @click="handleOpenDetail(row)"
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
          <div
            v-for="field in detailFields"
            :key="field.label"
            v-show="field.show"
            class="item"
          >
            <div class="key">{{ field.label }}：</div>
            <div
              class="value"
              :style="field.isTextarea ? 'line-height: 22px; padding-top: 10px' : ''"
            >
              {{ field.value || '--' }}
            </div>
          </div>
          <div
            v-if="!isMcpService"
            class="item"
          >
            <div class="key">{{ `API ${$t('列表')}：` }}</div>
            <div
              v-if="!isComponentApi && curRecord.grant_dimension !== 'resource'"
              class="value"
            >
              {{ $t('网关下所有资源') }}
            </div>
            <div
              v-else
              class="value"
              style="line-height: 22px; padding-top: 10px"
            >
              <bk-table
                :size="'small'"
                :data="isComponentApi ? curRecord.components : curRecord.resources"
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
          <!-- 工具列表（MCP服务才显示） -->
          <div
            v-else
            class="item"
          >
            <div class="key">{{ $t('工具列表') }}：</div>
            <div class="value">
              {{ curRecord.tool_names?.join(', ') || '--' }}
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
      const methodMap = {
        gateway: 'getApplyRecords',
        component: 'getSysApplyRecords',
        mcp: 'getMcpServerApplyRecords',
      };
      return methodMap[this.typeValue] || 'getApplyRecords';
    },
    curDetailDispatchMethod() {
      return this.typeValue === 'component' ? 'getSysApplyRecordDetail' : 'getApplyRecordDetail';
    },
    sliderTitle() {
      const typeMap = {
        gateway: `${this.$t('网关')} API`,
        component: `${this.$t('组件')} API`,
        mcp: ' MCP Server',
      };
      return this.$t('申请{n} 单据详情', { n: typeMap[this.typeValue] });
    },
    // 状态列表
    statusList() {
      if (this.isMcpService) {
        return [
          { id: 'approved', name: this.$t('通过') },
          { id: 'pending', name: this.$t('待审批') },
          { id: 'rejected', name: this.$t('已驳回') },
        ];
      }
      return [
        { id: 'approved', name: this.$t('全部通过') },
        { id: 'partial_approved', name: this.$t('部分通过') },
        { id: 'rejected', name: this.$t('已驳回') },
        { id: 'pending', name: this.$t('待审批') },
      ];
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
      const keywordConfig = {
        mcp: {
          name: this.$t('MCP Server 名称'),
          placeholder: this.$t('请输入MCP Server 名称'),
        },
        component: {
          name: this.$t('系统名称'),
          placeholder: this.$t('请输入系统名称'),
        },
        gateway: {
          name: this.$t('网关名称'),
          placeholder: this.$t('请输入网关名'),
        },
      };
      return [
        {
          name: keywordConfig[this.typeValue].name,
          id: 'keyword',
          placeholder: keywordConfig[this.typeValue].placeholder,
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
    // 是否为 MCP 服务类型
    isMcpService() {
      return this.typeValue === 'mcp';
    },
    searchPlaceholder() {
      const nameMap = {
        mcp: this.localLanguage === 'en' ? 'MCP Server' : ' MCP Server ',
        component: this.$t('系统'),
        gateway: this.$t('网关'),
      };
      return this.$t('请输入{n}名称/申请人', { n: nameMap[this.typeValue] });
    },
    // 详情侧栏的字段配置
    detailFields() {
      const fields = [
        {
          label: this.$t('申请人'),
          value: this.curRecord.applied_by,
          show: true,
        },
      ];
      // 授权维度（非组件API才显示）
      if (!this.isComponentApi) {
        fields.push({
          label: this.$t('授权维度'),
          value: this.isMcpService
            ? this.$t('按 MCP Service')
            : this.curRecord.grant_dimension === 'resource'
            ? this.$t('按资源')
            : this.$t('按网关'),
          show: true,
        });
      }
      fields.push(
        {
          label: this.$t('有效时间'),
          value:
            this.curRecord.expire_days === 0
              ? this.$t('永久')
              : Math.ceil(this.curRecord.expire_days / 30) + this.$t('个月'),
          show: true,
        },
        {
          label: this.$t('申请理由'),
          value: this.curRecord.reason,
          show: true,
        },
        {
          label: this.$t('申请时间'),
          value: this.curRecord.applied_time,
          show: true,
        },
        {
          label: this.$t('审批人'),
          value: this.getHandleBy(this.curRecord.handled_by),
          show: true,
        },
        {
          label: this.$t('审批时间'),
          value: this.curRecord.handled_time,
          show: true,
        },
        {
          label: this.$t('审批状态'),
          value: this.$t(this.curRecord.apply_status_display),
          show: true,
        },
        {
          label: this.$t('审批内容'),
          value: this.curRecord.comment,
          show: true,
          isTextarea: true,
        },
        {
          label: this.isMcpService
            ? this.$t('MCP Server')
            : this.isComponentApi
            ? this.$t('系统名称')
            : this.$t('网关名称'),
          value: this.isMcpService
            ? this.curRecord.name
            : this.isComponentApi
            ? this.curRecord.system_name
            : this.curRecord.api_name,
          show: true,
        }
      );
      return fields;
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
    getTypeLabel() {
      const typeMap = {
        gateway: this.$t('网关'),
        component: this.$t('系统'),
        mcp: this.$t('MCP Server'),
      };
      return typeMap[this.typeValue];
    },

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

    getStatusDisplay(status) {
      const data = this.statusList.find((item) => item.id === status);
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
      this.$nextTick(() => {
        this.$refs.tableRef?.doLayout();
      });
    },

    getHandleBy(payload) {
      return payload?.length ? payload.join('，') : '--';
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

    // mcp service 数据格式化
    formatMcpServiceData(data) {
      return data.map((item) => ({
        ...item.record,
        ...item.mcp_server,
        ...item,
      }));
    },

    // 获取申请记录
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
        const records = this.isMcpService ? this.formatMcpServiceData(res) : res.data?.results || [];
        records.forEach((item) => {
          item.type = this.typeValue;
        });
        this.pagination.count = this.isMcpService ? records.length : res.data.count;
        this.tableList = records;
        this.updateTableEmptyConfig();
        this.tableEmptyConf.isAbnormal = false;
      } catch (e) {
        this.tableEmptyConf.isAbnormal = true;
        this.catchErrorHandler(e);
      } finally {
        this.loading = false;
      }
    },

    // 详情侧栏
    async handleOpenDetail(row) {
      console.log('handleOpenDetail', row);
      this.detailSliderConf.show = true;
      // mcp service 使用当前行数据
      if (row.type === 'mcp') {
        this.curRecord = row;
        return;
      }
      this.detailLoading = true;
      try {
        const res = await this.$store.dispatch(`cloudApi/${this.curDetailDispatchMethod}`, {
          appCode: this.appCode,
          recordId: row.id,
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
  padding: 10px 12px;

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
      min-width: 115px;
      padding-right: 10px;
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
