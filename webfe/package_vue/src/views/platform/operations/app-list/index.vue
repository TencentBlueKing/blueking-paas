<template>
  <div class="platform-app-list-container">
    <div class="top-box flex-row justify-content-between">
      <div class="tenants">
        <TenantSelect
          class="tenant-select-cls"
          v-model="curTenantId"
          :panels="tabData"
          :label="$t('租户')"
          :count-map="appCountInfo"
          @change="getPlatformApps"
        />
      </div>
      <bk-input
        v-model="searchValue"
        :placeholder="$t('请输入应用名称、ID')"
        :right-icon="'bk-icon icon-search'"
        style="width: 480px"
        clearable
        @clear="handleSearch"
        @enter="handleSearch"
        @right-icon-click="handleSearch"
      ></bk-input>
    </div>
    <div class="card-style table-wrapper">
      <bk-table
        :data="appList"
        :pagination="pagination"
        ref="tableRef"
        size="small"
        v-bkloading="{ isLoading: isTableLoading, zIndex: 10 }"
        @page-change="pgHandlePageChange"
        @page-limit-change="pgHandlePageLimitChange"
        @filter-change="handleFilterChange"
        @sort-change="handleSortChange"
      >
        <div slot="empty">
          <table-empty
            :keyword="tableEmptyConf.keyword"
            :abnormal="tableEmptyConf.isAbnormal"
            :empty-title="$t('暂无应用')"
            @reacquire="getPlatformApps"
            @clear-filter="clearFilterKey"
          />
        </div>
        <bk-table-column
          v-for="column in columns"
          v-bind="column"
          :label="column.label"
          :prop="column.prop"
          :key="column.user"
          :show-overflow-tooltip="column.prop !== 'code'"
        >
          <template slot-scope="{ row }">
            <!-- logo/ 应用 -->
            <div
              v-if="column.prop === 'code'"
              class="flex-row align-items-center flex-nowrap"
            >
              <img
                :src="row.logo ? row.logo : '/static/images/default_logo.png'"
                class="app-logo"
              />
              <span
                class="text-ellipsis app-name"
                v-bk-overflow-tips
                @click="toAppDetail(row)"
              >
                {{ row[column.prop] }}
              </span>
            </div>
            <!-- 租户类型 -->
            <div v-else-if="column.prop === 'app_tenant_mode'">
              {{ row[column.prop] === 'single' ? $t('单租户') : $t('全租户') }}
            </div>
            <div v-else-if="column.prop === 'resource_quotas'">
              {{ row[column.prop] ? `${row[column.prop].cpu}/${row[column.prop].memory}` : '--' }}
            </div>
            <div
              v-else-if="column.prop === 'is_active'"
              class="flex-row align-items-center"
            >
              <i :class="['dot', { successful: row.is_active }]"></i>
              <span :class="{ 'off-shelf': !row.is_active }">
                {{ row.is_active ? $t('正常') : $t('下架') }}
              </span>
            </div>
            <bk-user-display-name
              v-else-if="column.userDisplay && platformFeature.MULTI_TENANT_MODE"
              :user-id="row[column.prop]"
            ></bk-user-display-name>
            <span v-else>{{ row[column.prop] || '--' }}</span>
          </template>
        </bk-table-column>
      </bk-table>
    </div>
  </div>
</template>

<script>
import TenantSelect from '../../services/service-plan/tenant-select';
import { mapState } from 'vuex';

export default {
  name: 'PlatformAppList',
  components: {
    TenantSelect,
  },
  props: {
    tenants: {
      type: Array,
      default: () => [],
    },
  },
  data() {
    return {
      // 当前table租户
      curTenantId: 'all',
      searchValue: '',
      appList: [],
      isTableLoading: false,
      pagination: {
        current: 1,
        count: 0,
        limit: 10,
        limitList: [5, 10, 15, 20],
      },
      // 应用数量信息
      appCountInfo: {},
      // 应用类型
      appTypes: [],
      // 租户类型
      tenantTypes: [],
      // 表头过滤
      tableFilterMap: {},
      tableEmptyConf: {
        keyword: '',
        isAbnormal: false,
      },
    };
  },
  computed: {
    ...mapState(['platformFeature']),
    tabData() {
      const tenantList = this.tenants.map((item) => {
        return {
          name: item.id,
          label: item.name,
        };
      });
      return [
        {
          name: 'all',
          label: this.$t('全部租户'),
        },
        ...tenantList,
      ];
    },
    columns() {
      return [
        {
          label: this.$t('应用'),
          prop: 'code',
        },
        {
          label: this.$t('租户类型'),
          prop: 'app_tenant_mode',
          filters: this.tenantTypes,
          'filter-multiple': false,
          'column-key': 'app_tenant_mode',
        },
        {
          label: this.$t('所属租户'),
          prop: 'app_tenant_id',
        },
        {
          label: this.$t('应用类型'),
          prop: 'type',
          filters: this.appTypes,
          'filter-multiple': false,
          'column-key': 'type',
        },
        {
          label: this.$t('资源配额'),
          prop: 'resource_quotas',
        },
        {
          label: this.$t('状态'),
          prop: 'is_active',
          filters: [
            { text: this.$t('正常'), value: true },
            { text: this.$t('下架'), value: false },
          ],
          'filter-multiple': false,
          'column-key': 'is_active',
        },
        {
          label: this.$t('创建人'),
          prop: 'creator',
          userDisplay: true,
        },
        {
          label: this.$t('创建时间'),
          prop: 'created_humanized',
          sortable: true,
          'column-key': 'order_by',
        },
      ];
    },
  },
  async created() {
    await this.getPlatformApps();
    Promise.all([this.getTenantAppStatistics(), this.getTenantModeList(), this.getAppTypes()]);
  },
  methods: {
    // 页码重置
    resetPage() {
      this.pagination.current = 1;
    },
    // 页容量改变
    pgHandlePageLimitChange(limit) {
      this.resetPage();
      this.pagination.limit = limit;
      this.getPlatformApps();
    },
    // 页码改变
    pgHandlePageChange(page) {
      this.pagination.current = page;
      this.getPlatformApps();
    },
    transformData(data) {
      // 获取对象中的第一个属性名
      const key = Object.keys(data)[0];
      // 创建一个新的对象，将第一个属性的第一个数组元素提取为值
      return {
        [key]: data[key][0],
      };
    },
    // 表头筛选
    handleFilterChange(filter) {
      this.tableFilterMap = Object.assign(this.tableFilterMap, { ...this.transformData(filter) });
      this.handleSearch();
    },
    // 过滤掉属性为undefined的字段
    filterUndefinedProperties(originalObject) {
      const filteredObject = {};
      Object.entries(originalObject).forEach(([key, value]) => {
        // 仅当值不为 undefined 时才添加到新对象中
        if (value !== undefined) {
          filteredObject[key] = value;
        }
      });
      return filteredObject;
    },
    // 表头排序-时间
    handleSortChange(sort) {
      const orderBy = sort.order ? (sort.order === 'ascending' ? '-created' : 'created') : undefined;
      this.$set(this.tableFilterMap, 'order_by', orderBy);
      this.getPlatformApps();
    },
    // 搜索
    handleSearch() {
      this.resetPage();
      this.getPlatformApps();
    },
    // 处理列表请求参数
    constructQueryParams() {
      const { limit, current } = this.pagination;
      // 表头筛选，过滤掉 `undefined` 的字段
      const filteredData = this.filterUndefinedProperties(this.tableFilterMap);
      const queryParams = {
        limit,
        offset: limit * (current - 1),
        ...filteredData,
      };
      if (this.searchValue) {
        queryParams.search = this.searchValue;
      }
      // 所属租户
      if (this.curTenantId !== 'all') {
        queryParams.app_tenant_id = this.curTenantId;
      }
      return queryParams;
    },
    // 获取应用列表
    async getPlatformApps() {
      this.isTableLoading = true;
      const queryParams = this.constructQueryParams();
      try {
        const res = await this.$store.dispatch('tenantOperations/getPlatformApps', { queryParams });
        this.appList = res.results;
        this.pagination.count = res.count;
        this.tableEmptyConf.isAbnormal = false;
        this.updateTableEmptyConfig();
      } catch (e) {
        this.tableEmptyConf.isAbnormal = true;
        this.catchErrorHandler(e);
      } finally {
        this.isTableLoading = false;
      }
    },
    // 获取应用数量信息
    async getTenantAppStatistics() {
      try {
        const res = await this.$store.dispatch('tenantOperations/getTenantAppStatistics');
        // 全部租户
        this.$set(this.appCountInfo, 'all', this.pagination.count);
        res.forEach((item) => {
          this.$set(this.appCountInfo, item.tenant_id, item.app_count);
        });
      } catch (e) {
        this.catchErrorHandler(e);
      }
    },
    // 获取租户应用数量
    async getTenantAppStatistics() {
      try {
        const res = await this.$store.dispatch('tenantOperations/getTenantAppStatistics');
        // 全部租户
        this.$set(this.appCountInfo, 'all', this.pagination.count);
        res.forEach((item) => {
          this.$set(this.appCountInfo, item.tenant_id, item.app_count);
        });
      } catch (e) {
        this.catchErrorHandler(e);
      }
    },
    // 获取租户类型
    async getTenantModeList() {
      try {
        const res = await this.$store.dispatch('tenantOperations/getTenantModeList');
        this.tenantTypes = res.map((item) => ({
          value: item.type,
          text: item.label,
        }));
      } catch (e) {
        this.catchErrorHandler(e);
      }
    },
    // 获取应用类型
    async getAppTypes() {
      try {
        const res = await this.$store.dispatch('tenantOperations/getAppTypes');
        this.appTypes = res.map((item) => ({
          value: item.type,
          text: item.label,
        }));
      } catch (e) {
        this.catchErrorHandler(e);
      }
    },
    // 跳转应用详情
    toAppDetail(data) {
      this.$router.push({
        name: 'platformAppDetails',
        params: {
          code: data.code,
        },
        query: {
          active: 'overview',
        },
      });
    },
    // 清空搜索筛选条件
    clearFilterKey() {
      this.tableFilterMap = {};
      this.searchValue = '';
      this.$refs.tableRef?.clearFilter();
    },
    updateTableEmptyConfig() {
      const filteredData = this.filterUndefinedProperties(this.tableFilterMap);
      if (this.searchValue || Object.keys(filteredData)?.length) {
        this.tableEmptyConf.keyword = 'placeholder';
        return;
      }
      this.tableEmptyConf.keyword = '';
    },
  },
};
</script>

<style lang="scss" scoped>
.platform-app-list-container {
  .card-style {
    padding: 16px;
  }
  .table-wrapper {
    margin-top: 16px;
    .app-logo {
      width: 24px;
      height: 24px;
      border-radius: 2px;
      margin-right: 16px;
    }
    .app-name {
      color: #3a84ff;
      cursor: pointer;
    }
    i.dot {
      display: inline-block;
      margin-right: 8px;
      width: 13px;
      height: 13px;
      border-radius: 50%;
      background: #979ba5;
      border: 3px solid #979ba5;
      &.successful {
        background: #3fc06d;
        border: 3px solid #daf6e5;
      }
    }
  }
  .tenants {
    .tenant-select-cls {
      background: #fff;
    }
  }
}
</style>
