<template>
  <div class="bk-plugin-wrapper right-main-plugin">
    <paas-content-loader
      :is-loading="loading"
      placeholder="pluin-list-loading"
      offset-top="20"
      class="wrap"
      :height="575"
      :is-transform="false"
    >
      <div class="flex-row justify-content-between">
        <bk-button
          theme="primary"
          @click="createPlugin"
        >
          {{ $t('创建插件') }}
        </bk-button>
        <!-- 过滤参数 -->
        <div class="flex-row justify-content-between">
          <filter-select
            class="mt0"
            @change="handleFiltersChange"
          />
          <bk-input
            v-model="filterKey"
            class="paas-plugin-input"
            :placeholder="$t('输入插件ID、插件名称，按Enter搜索')"
            :clearable="true"
            :right-icon="'paasng-icon paasng-search'"
            @enter="handleSearch"
            @right-icon-click="handleSearch"
          />
        </div>
      </div>
      <bk-table
        ref="pluginTable"
        v-bkloading="{ isLoading: isDataLoading }"
        :data="pluginList"
        size="small"
        ext-cls="plugin-list-table"
        :pagination="pagination"
        :show-overflow-tooltip="true"
        @page-limit-change="handlePageLimitChange"
        @page-change="handlePageChange"
        @filter-change="handleFilterChange"
      >
        <div slot="empty">
          <table-empty
            :keyword="tableEmptyConf.keyword"
            :abnormal="tableEmptyConf.isAbnormal"
            @reacquire="fetchPluginsList"
            @clear-filter="clearFilterKey"
          />
        </div>
        <bk-table-column
          :label="$t('插件 ID')"
          :render-header="$renderHeader"
        >
          <template #default="{ row }">
            <span
              class="plugin-link"
              @click="toPluginSummary(row)"
            >
              <img
                :src="row.logo"
                onerror="this.src='/static/images/plugin-default.svg'"
                class="plugin-logo-cls"
              />
              {{ row.id || '--' }}
            </span>
          </template>
        </bk-table-column>
        <bk-table-column
          :label="$t('插件名称')"
          :render-header="$renderHeader"
        >
          <template #default="{ row }">
            <span>{{ row.name_zh_cn }}</span>
          </template>
        </bk-table-column>
        <bk-table-column
          :label="$t('插件类型')"
          prop="pd_name"
          column-key="pd_name"
          :filters="pluginTypeFilters"
          :filter-multiple="true"
          :render-header="$renderHeader"
        >
          <template #default="{ row }">
            {{ row.pd_name || '--' }}
          </template>
        </bk-table-column>
        <bk-table-column
          :label="$t('创建时间')"
          prop="created"
          :render-header="$renderHeader"
        >
          <template #default="{ row }">
            {{ row.created || '--' }}
          </template>
        </bk-table-column>
        <bk-table-column
          :label="$t('开发语言')"
          prop="language"
          column-key="language"
          :filters="languageFilters"
          :filter-multiple="true"
          :render-header="$renderHeader"
        />
        <bk-table-column
          :label="$t('是否已下架')"
          prop="status"
          column-key="status"
          :filter-multiple="false"
          :filters="statusFilters"
          :render-header="$renderHeader"
        >
          <template #default="{ row }">
            {{ row.status === 'archived' ? $t('是') : $t('否') }}
          </template>
        </bk-table-column>
        <bk-table-column :label="$t('版本')">
          <template #default="{ row }">
            <template v-if="row.latest_release">
              <round-loading v-if="releaseStatusMap[row.latest_release.status]" />
              <div
                v-else
                :class="['dot', row.latest_release.status]"
              />
              {{ row.latest_release.version }}
            </template>
            <template v-else>--</template>
          </template>
        </bk-table-column>
        <bk-table-column
          :label="$t('操作')"
          :width="localLanguage === 'en' ? 280 : 220"
        >
          <template #default="{ row }">
            <div :class="['table-operate-buttons', localLanguage === 'en' ? 'en-operate' : 'zh-operate']">
              <bk-button
                v-if="row.status === 'waiting-approval' || row.status === 'approval-failed'"
                theme="primary"
                size="small"
                text
                @click="toParticulars(row)"
              >
                {{ $t('审批详情') }}
              </bk-button>
              <template v-else>
                <bk-button
                  theme="primary"
                  size="small"
                  text
                  @click="toNewVersion(row)"
                >
                  {{
                    row.ongoing_release && releaseStatusMap[row.ongoing_release.status] ? $t('发布进度') : $t('发布')
                  }}
                </bk-button>
                <bk-button
                  class="versions-btn"
                  theme="primary"
                  size="small"
                  text
                  @click="toDetail(row)"
                >
                  {{ $t('版本管理') }}
                </bk-button>
              </template>
              <bk-button
                v-if="row.status === 'approval-failed'"
                class="del-btn"
                theme="primary"
                size="small"
                text
                @click="deletePlugin(row)"
              >
                {{ $t('删除') }}
              </bk-button>
            </div>
          </template>
        </bk-table-column>
      </bk-table>
    </paas-content-loader>

    <bk-dialog
      v-model="removePluginDialog.visiable"
      width="420"
      :title="$t('确定删除插件')"
      :theme="'primary'"
      :mask-close="false"
      :loading="removePluginDialog.isLoading"
      @confirm="handlerDeletePlugin"
    >
      <div>{{ $t('是否确定删除') }} {{ removePluginDialog.selectedPlugin.id }}</div>
    </bk-dialog>
  </div>
</template>

<script>
import { PLUGIN_STATUS } from '@/common/constants';
import { clearFilter } from '@/common/utils';
import filterSelect from './comps/filter-select.vue';
export default {
  components: { filterSelect },
  data() {
    return {
      loading: true,
      filterKey: '',
      pluginList: [],
      pluginStatus: PLUGIN_STATUS,
      isDataLoading: true,
      pagination: {
        current: 1,
        limit: 10,
        limitList: [5, 10, 20, 50],
        count: 0,
      },
      isFilter: false,
      filterLanguage: [],
      filterPdName: [],
      languageFilters: [],
      filterStatus: [],
      statusFilters: [
        {
          value: 'archived',
          text: this.$t('是'),
        },
        {
          value: 'no',
          text: this.$t('否'),
        },
      ],
      pluginTypeFilters: [],
      removePluginDialog: {
        visiable: false,
        isLoading: false,
        selectedPlugin: {},
      },
      releaseStatusMap: {
        pending: 'pending',
        initial: 'initial',
      },
      tableEmptyConf: {
        keyword: '',
        isAbnormal: false,
      },
      orderBy: '-updated',
    };
  },
  computed: {
    localLanguage() {
      return this.$store.state.localLanguage;
    },
  },
  watch: {
    filterKey(newVal, oldVal) {
      if (newVal === '' && oldVal !== '') {
        if (this.isFilter) {
          this.fetchPluginsList();
          this.isFilter = false;
        }
      }
    },
    filterLanguage() {
      this.fetchPluginsList();
    },
    filterPdName() {
      this.fetchPluginsList();
    },
    filterStatus() {
      this.fetchPluginsList();
    },
  },
  mounted() {
    this.fetchPluginsList();
    this.getPluginFilterParams();
  },
  methods: {
    async fetchPluginsList(page = 1) {
      try {
        const curPage = page || this.pagination.current;
        const pageParams = {
          limit: this.pagination.limit,
          offset: this.pagination.limit * (curPage - 1),
          order_by: this.orderBy,
          search_term: this.filterKey,
        };
        const statusParams = this.formatFilterParams('filterStatus', 'status');
        const languageParams = this.formatFilterParams('filterLanguage', 'language');
        const pdIdParams = this.formatFilterParams('filterPdName', 'pd__identifier');
        this.isDataLoading = true;
        const res = await this.$store.dispatch('plugin/getPlugins', {
          pageParams,
          statusParams,
          languageParams,
          pdIdParams,
        });
        this.pluginList = res.results;
        this.pagination.count = res.count;
        this.updateTableEmptyConfig();
        this.tableEmptyConf.isAbnormal = false;
      } catch (e) {
        // 显示异常
        this.tableEmptyConf.isAbnormal = true;
        this.$paasMessage({
          limit: 1,
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      } finally {
        this.isDataLoading = false;
        this.loading = false;
      }
    },

    /**
     * 格式化query参数
     * dataName: 数据源key
     * key：query参数名
     */
    formatFilterParams(dataName, key) {
      if (key === 'status' && this[dataName].includes('no')) {
        // 查询未下架的所有状态
        return 'status=developing&status=releasing&status=released&status=waiting-approval&status=approval-failed';
      }

      return this[dataName].reduce((paramsText, item) => `${paramsText}${key}=${item}&`, '').slice(0, -1);
    },

    async getPluginFilterParams() {
      try {
        const res = await this.$store.dispatch('plugin/getPluginFilterParams');
        // 开发语言
        res.languages.forEach((value) => {
          this.languageFilters.push({
            value,
            text: value,
          });
        });
        // 插件类型
        res.plugin_types.forEach((value) => {
          this.pluginTypeFilters.push({
            value: value.id,
            text: value.name,
          });
        });
      } catch (e) {
        this.$bkMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      }
    },

    deletePlugin(row) {
      this.removePluginDialog.visiable = true;
      this.removePluginDialog.selectedPlugin = row;
    },

    async handlerDeletePlugin() {
      try {
        this.removePluginDialog.isLoading = true;
        await this.$store.dispatch('plugin/deletePlugin', {
          pdId: this.removePluginDialog.selectedPlugin.pd_id,
          pluginId: this.removePluginDialog.selectedPlugin.id,
        });
        this.$bkMessage({
          theme: 'success',
          message: this.$t('删除成功！'),
        });
        this.removePluginDialog.visiable = false;
        this.fetchPluginsList();
      } catch (e) {
        this.$bkMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      } finally {
        this.removePluginDialog.isLoading = false;
      }
    },

    handlePageLimitChange(limit) {
      this.pagination.limit = limit;
      this.pagination.current = 1;
      this.fetchPluginsList(this.pagination.current);
    },

    handlePageChange(newPage) {
      this.pagination.current = newPage;
      this.fetchPluginsList(newPage);
    },

    handleFilterChange(filters) {
      if (filters.language) {
        this.filterLanguage = filters.language.length ? filters.language : [];
      }

      if (filters.pd_name) {
        this.filterPdName = filters.pd_name.length ? filters.pd_name : [];
      }

      // 是否下架筛选
      if (filters.status) {
        this.filterStatus = filters.status.length ? filters.status : [];
      }
    },

    handleSearch() {
      // API 发布
      if (this.filterKey === '') {
        return;
      }
      this.isFilter = true;
      this.fetchPluginsList();
    },

    createPlugin() {
      this.$router.push({
        name: 'createPlugin',
      });
    },

    toPluginSummary(data) {
      this.$router.push({
        name: 'pluginSummary',
        params: { pluginTypeId: data.pd_id, id: data.id },
      });
    },

    toParticulars(data) {
      if (data.itsm_detail) {
        window.open(data.itsm_detail.ticket_url, '_blank');
      }
    },

    toNewVersion(data) {
      if (data.ongoing_release && this.releaseStatusMap[data.ongoing_release.status]) {
        this.$router.push({
          name: 'pluginVersionRelease',
          params: { pluginTypeId: data.pd_id, id: data.id },
          query: {
            release_id: data.ongoing_release.id,
          },
        });
      } else {
        this.$router.push({
          name: 'pluginVersionEditor',
          params: { pluginTypeId: data.pd_id, id: data.id },
          query: {
            type: 'prod',
          },
        });
      }
    },

    toDetail(data) {
      this.$router.push({
        name: 'pluginVersionManager',
        params: { pluginTypeId: data.pd_id, id: data.id }, // pluginTypeId插件类型标识 id插件标识
      });
    },

    clearFilterKey() {
      this.filterKey = '';
      this.$refs.pluginTable.clearFilter();
      // 手动清空表头筛选
      if (this.$refs.pluginTable.$refs.tableHeader) {
        const { tableHeader } = this.$refs.pluginTable.$refs;
        clearFilter(tableHeader);
      }
      this.fetchPluginsList();
    },

    updateTableEmptyConfig() {
      if (this.filterKey || this.filterLanguage.length || this.filterPdName.length || this.filterStatus.length) {
        this.tableEmptyConf.keyword = 'placeholder';
        return;
      }
      this.tableEmptyConf.keyword = '';
    },

    // 插件列表过滤参数变化
    handleFiltersChange(orderBy) {
      this.orderBy = orderBy;
      this.fetchPluginsList();
    },
  },
};
</script>

<style lang="scss" scoped>
.bk-plugin-wrapper {
  margin-top: 74px;
  width: 100%;
  .paas-plugin-tit {
    padding: 12px 0 16px;
    color: #666;
    line-height: 18px;
    position: relative;
  }

  .paas-plugin-tit h3 {
    font-size: 18px;
    font-weight: normal;
    display: inline-block;
    color: #313238;
  }

  .paas-plugin-input {
    width: 360px;
  }

  .plugin-list-table {
    margin-top: 16px;
    :deep(.bk-table-pagination-wrapper) {
      background: #fff;
    }
    .point {
      height: 8px;
      width: 8px;
      display: inline-block;
      border-radius: 50%;
      margin-right: 3px;
      border: 1px solid #ff9c01;
    }
    .waiting-approval {
      background: #ffe8c3;
      border: 1px solid #ff9c01;
    }

    .approval-failed {
      background: #ffeded;
      border-color: #ffdddd;
    }

    .developing {
      background: #f0f1f5;
      border: 1px solid #c4c6cc;
    }

    .released {
      background: #e5f6ea;
      border: 1px solid #3fc06d;
    }
    .failed {
      background: #ffeded;
      border-color: #ffdddd;
    }

    .dot {
      height: 8px;
      width: 8px;
      display: inline-block;
      border-radius: 50%;
      margin-right: 3px;
    }
    .dot.successful {
      background: #e5f6ea;
      border: 1px solid #3fc06d;
    }

    .dot.failed,
    .dot.interrupted {
      background: #ffe6e6;
      border: 1px solid #ea3636;
    }
  }

  .bk-button-text.bk-button-small {
    padding: 0 3px;
    line-height: 26px;
  }
}
.wrap {
  width: calc(100% - 120px);
}
.plugin-logo-cls {
  width: 16px;
  vertical-align: middle;
}
.empty-tips {
  margin-top: 5px;
  color: #979ba5;
  .clear-search {
    cursor: pointer;
    color: #3a84ff;
  }
}
.plugin-link {
  color: #3a84ff;
  cursor: pointer;
  &:hover {
    color: #699df4;
  }
}
</style>

<style lang="scss">
.bk-plugin-wrapper .exception-wrap-item .bk-exception-img.part-img {
  height: 130px;
}
.bk-plugin-wrapper .bk-table th .bk-table-column-filter-trigger.is-filtered {
  color: #3a84ff !important;
}
.bk-plugin-wrapper {
  .table-operate-buttons .bk-button-text > div {
    text-align: left;
  }
  .table-operate-buttons.en-operate .bk-button-text > div {
    width: 92px !important;
  }
  .table-operate-buttons.zh-operate .bk-button-text > div,
  .table-operate-buttons.en-operate .versions-btn > div,
  .table-operate-buttons.en-operate .del-btn > div {
    width: 50px !important;
  }
}
</style>
