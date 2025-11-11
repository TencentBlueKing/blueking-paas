<template>
  <div
    :class="['marked-apps-container', { 'center-cls': !allMarkedApps.length && !isLoading }]"
    ref="contentRef"
  >
    <!-- 暂无收藏应用 -->
    <section
      v-if="!allMarkedApps.length && !isLoading"
      class="not-marked-apps"
    >
      <div class="empty-image">
        <img src="/static/images/home-marked-empty.png" />
      </div>
      <p class="empty-sub-title mt-24">{{ $t('暂无收藏的应用') }}</p>
      <p class="empty-text mt-8">{{ $t('将鼠标悬浮到应用，点击收藏图标') }}</p>
    </section>
    <bk-table
      v-else
      :data="markedApps"
      ref="tableRef"
      size="medium"
      :max-height="tableMaxHeight"
      v-bkloading="{ isLoading: isLoading, zIndex: 10 }"
      ext-cls="marked-apps-table"
      :row-class-name="getRowClassName"
      @filter-change="handleFilterChange"
    >
      <div slot="empty">
        <table-empty
          :keyword="hasFilterCondition"
          @clear-filter="clearFilterKey"
        />
      </div>
      <bk-table-column
        :label="$t('应用')"
        prop="name"
        :min-width="280"
      >
        <template slot-scope="{ row }">
          <div class="app-name flex-row align-items-center">
            <img
              :src="row.application?.logo_url || defaultImg"
              class="app-logo"
            />
            <div class="info flex-row flex-column">
              <span
                class="name"
                @click="toAppSummary(row)"
              >
                {{ row.application?.name }}
              </span>
              <span class="code">{{ row.application?.code }}</span>
            </div>
          </div>
        </template>
      </bk-table-column>
      <bk-table-column
        :label="$t('模块数量')"
        prop="name"
      >
        <template slot-scope="{ row }">
          {{ $t('共') }}&nbsp; {{ row.application.modules?.length }} &nbsp;{{ $t('个模块') }}
        </template>
      </bk-table-column>
      <template v-if="isShowTenant">
        <bk-table-column
          :label="$t('租户模式')"
          prop="app_tenant_mode"
          column-key="app_tenant_mode"
          :filters="tenantFilters"
          :filter-multiple="false"
        >
          <template slot-scope="{ row }">
            {{ $t(appTenantMode[row.application.app_tenant_mode]) }}
          </template>
        </bk-table-column>
        <bk-table-column :label="$t('租户 ID')">
          <template slot-scope="{ row }">
            {{ row.application?.app_tenant_id || '--' }}
          </template>
        </bk-table-column>
      </template>
      <bk-table-column
        :label="$t('状态')"
        :render-header="statusRenderHeader"
      >
        <template slot-scope="{ row }">
          <span :class="['g-dot-default mr8', { success: row.application.is_active }]"></span>
          <span>
            {{ row.application?.is_active ? $t('正常') : $t('下架') }}
          </span>
        </template>
      </bk-table-column>
      <bk-table-column
        :label="$t('操作')"
        :width="240"
      >
        <template slot-scope="{ row }">
          <span
            v-for="env in ['stag', 'prod']"
            :key="env"
          >
            <bk-button
              :disabled="!row.application.deploy_info?.[env]?.deployed"
              text
              :class="{ mr10: env === 'stag' }"
              @click="visitLink(row, env)"
            >
              <span
                v-bk-tooltips="{
                  content: $t('应用未部署，不能访问'),
                  placement: 'top',
                  allowHTML: true,
                  disabled: row.application.deploy_info?.[env]?.deployed,
                }"
              >
                {{ $t(env === 'stag' ? '访问预发布环境' : '访问生产环境') }}
              </span>
            </bk-button>
          </span>
        </template>
      </bk-table-column>
    </bk-table>
  </div>
</template>

<script>
import tebleHeaderFilters from '@/components/teble-header-filters';
import { mapGetters } from 'vuex';
import { APP_TENANT_MODE } from '@/common/constants';

export default {
  data() {
    return {
      isLoading: true,
      containerHeight: 0,
      resizeObserver: null,
      allMarkedApps: [],
      markedApps: [],
      appTenantMode: APP_TENANT_MODE,
      tenantFilters: [
        { text: this.$t('单租户'), value: 'single' },
        { text: this.$t('全租户'), value: 'global' },
      ],
      tableHeaderFilterValue: 'all',
      currentTenantFilters: [], // 当前租户模式过滤条件
    };
  },
  computed: {
    ...mapGetters(['isShowTenant']),
    tableMaxHeight() {
      if (this.containerHeight <= 0) {
        return 500;
      }
      // 表格最大高度与容器高度一致
      return this.containerHeight;
    },
    hasFilterCondition() {
      if (this.currentTenantFilters.length > 0 || this.tableHeaderFilterValue !== 'all') {
        // 存在筛选条件，默认为 placeholder
        return 'placeholder';
      }
      return '';
    },
  },
  created() {
    this.getMarkedApps();
  },
  mounted() {
    this.initResizeObserver();
  },
  beforeDestroy() {
    if (this.resizeObserver) {
      this.resizeObserver.disconnect();
      this.resizeObserver = null;
    }
  },
  methods: {
    handleFilterChange(filter) {
      if (filter.app_tenant_mode) {
        this.currentTenantFilters = filter.app_tenant_mode;
        this.applyAllFilters();
      }
    },
    // 初始化 ResizeObserver
    initResizeObserver() {
      if (typeof ResizeObserver !== 'undefined') {
        this.resizeObserver = new ResizeObserver((entries) => {
          for (const entry of entries) {
            this.containerHeight = entry.contentRect.height;
          }
        });
        // 开始观察容器元素
        this.resizeObserver.observe(this.$refs?.contentRef);
      } else {
        // 如果浏览器不支持 ResizeObserver，使用默认高度
        this.containerHeight = 500;
      }
    },
    // 获取行的 class 名称
    getRowClassName({ row }) {
      return !row.application.is_active ? 'off-shelf-row' : '';
    },
    // 获取收藏的应用列表
    async getMarkedApps() {
      this.isLoading = true;
      try {
        const queryParams = `${BACKEND_URL}/api/bkapps/applications/lists/detailed?format=json&is_marked=true`;
        const { results = [] } = await this.$store.dispatch('getAppList', { url: queryParams });
        this.markedApps = results;
        this.allMarkedApps = results;
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.isLoading = false;
        bus.$emit('on-close-loading');
      }
    },
    statusRenderHeader(h) {
      return h(tebleHeaderFilters, {
        props: {
          active: this.tableHeaderFilterValue,
          label: this.$t('状态'),
          iconClass: 'bk-icon icon-funnel',
          filterList: [
            { text: this.$t('全部'), value: 'all' },
            { text: this.$t('正常'), value: 'normal' },
            { text: this.$t('下架'), value: 'archive' },
          ],
        },
        on: {
          'filter-change': (data) => {
            this.tableHeaderFilterValue = data.value;
            this.applyAllFilters();
          },
        },
      });
    },
    // 应用所有过滤条件
    applyAllFilters() {
      let filteredApps = this.allMarkedApps;

      // 应用状态过滤
      const statusFilterConditions = {
        all: () => true,
        normal: (item) => item.application.is_active,
        archive: (item) => !item.application.is_active,
      };
      const statusFilterFunction = statusFilterConditions[this.tableHeaderFilterValue] || (() => true);
      filteredApps = filteredApps.filter(statusFilterFunction);

      // 应用租户模式过滤
      if (this.currentTenantFilters && this.currentTenantFilters.length > 0) {
        filteredApps = filteredApps.filter((item) => {
          return this.currentTenantFilters.includes(item.application.app_tenant_mode);
        });
      }

      this.markedApps = filteredApps;
    },
    clearFilterKey() {
      this.$refs.tableRef?.clearFilter();
      this.currentTenantFilters = [];
      this.tableHeaderFilterValue = 'all';
      this.applyAllFilters();
    },
    // 跳转到应用概览
    toAppSummary(appItem) {
      const { type, code, modules = [] } = appItem.application || {};
      const routeName = type === 'cloud_native' ? 'cloudAppSummary' : 'appSummary';
      this.$router.push({
        name: routeName,
        params: {
          id: code,
          moduleId: modules.find((item) => item.is_default).name,
        },
      });
    },
    // 访问对应环境
    visitLink(data, env) {
      // 当 preferred_prod_url 有值时，生产环境的访问链接指向 preferred_prod_url
      let url = data.application.deploy_info[env].url;
      if (env === 'prod' && data.application.preferred_prod_url) {
        url = data.application.preferred_prod_url;
      }
      window.open(url);
    },
  },
};
</script>

<style lang="scss" scoped>
.marked-apps-container {
  height: 100%;
  &.center-cls {
    display: flex;
    justify-content: center;
    align-items: center;
  }
  .marked-apps-table {
    .app-name {
      .app-logo {
        width: 32px;
        height: 32px;
        border-radius: 4px;
        margin-right: 12px;
      }
      .info {
        .name {
          font-weight: 700;
          font-size: 12px;
          color: #3a84ff;
          cursor: pointer;
        }
        .code {
          font-size: 12px;
          color: #63656e;
        }
      }
    }
    /deep/ .off-shelf-row {
      color: #c4c6cc !important;
      .app-name .info .name {
        color: #c4c6cc !important;
      }
      .app-name .info .code {
        color: #c4c6cc !important;
      }
    }
  }
  .not-marked-apps {
    text-align: center;
    .empty-image {
      width: 220px;
      height: 220px;
      border-radius: 50%;
      overflow: hidden;
      img {
        width: 100%;
        height: 100%;
      }
    }
    .empty-sub-title {
      font-size: 16px;
      color: #4d4f56;
      line-height: 24px;
    }
    .empty-text {
      color: #979ba5;
    }
  }
}
</style>
