<template lang="html">
  <div class="container biz-create-success">
    <paas-content-loader
      class="app-container middle"
      :is-loading="isLoading"
      placeholder="pluin-list-loading"
    >
      <div class="middle">
        <paas-plugin-title />
        <div class="ag-top-header">
          <!-- 有发布任务，禁用 -->
          <div
            v-bk-tooltips.top="{ content: $t('已有发布任务进行中'), disabled: !curIsPending }"
            style="display: inline-block"
          >
            <bk-button
              theme="primary"
              class="mr10"
              :disabled="curIsPending && !pluginFeatureFlags.ALLOW_MULTIPLE_TEST_VERSIONS"
              @click="handleCreateVersion('formal')"
            >
              {{ $t('新建版本') }}
            </bk-button>
          </div>
          <span v-bk-tooltips="{ content: accessDisabledTips, disabled: !isAccessDisabled }">
            <bk-button
              v-if="pluginFeatureFlags.SHOW_ENTRANCES_ADDRESS"
              text
              theme="primary"
              :disabled="isAccessDisabled"
              @click="handleOpenLink"
            >
              {{ $t('插件访问入口') }}
              <i class="paasng-icon paasng-jump-link icon-cls-link mr5 copy-text" />
            </bk-button>
          </span>
          <bk-input
            v-model="keyword"
            class="fr"
            :clearable="true"
            :placeholder="$t('版本号、代码分支')"
            :right-icon="'bk-icon icon-search'"
            style="width: 480px"
            @enter="handleSearch"
          />
        </div>

        <bk-table
          ref="versionTable"
          v-bkloading="{ isLoading: isTableLoading }"
          class="ps-version-list"
          :data="versionList"
          :outer-border="false"
          :size="'small'"
          :pagination="pagination"
          @page-limit-change="limitChange"
          @page-change="pageChange"
          @filter-change="handleFilterChange"
        >
          <!-- 如果存在数据展示默认Exception -->
          <div slot="empty">
            <table-empty
              :keyword="tableEmptyConf.keyword"
              :abnormal="tableEmptyConf.isAbnormal"
              @reacquire="getVersionList"
              @clear-filter="clearFilterKey"
            />
          </div>
          <bk-table-column
            :label="$t('版本')"
            prop="version"
            :show-overflow-tooltip="true"
          >
            <template slot-scope="{ row }">
              <span
                v-bk-tooltips="row.version"
                :class="{ 'version-num': row.version }"
                style="cursor: pointer"
                @click="handleDetail(row)"
              >
                {{ row.version || '--' }}
              </span>
            </template>
          </bk-table-column>
          <bk-table-column
            :label="$t('代码分支')"
            prop="source_version_name"
            :render-header="$renderHeader"
          >
            <template slot-scope="{ row }">
              <span>{{ row.source_version_name || '--' }}</span>
            </template>
          </bk-table-column>
          <bk-table-column
            :label="$t('代码 Commit')"
            prop="comment"
            :render-header="$renderHeader"
          >
            <template slot-scope="{ row }">
              <span>{{ row.source_hash || '--' }}</span>
            </template>
          </bk-table-column>
          <bk-table-column
            :label="$t('创建人')"
            prop="creator"
            :render-header="$renderHeader"
          >
            <template slot-scope="{ row }">
              <span>{{ row.creator || '--' }}</span>
            </template>
          </bk-table-column>
          <bk-table-column
            :label="$t('创建时间')"
            prop="created"
            :render-header="$renderHeader"
          >
            <template slot-scope="{ row }">
              <span>{{ row.created || '--' }}</span>
            </template>
          </bk-table-column>
          <bk-table-column
            :label="$t('状态')"
            prop="status"
            column-key="status"
            :filters="statusFilters"
            :filter-multiple="true"
          >
            <template slot-scope="{ row }">
              <round-loading v-if="row.status === 'pending' || row.status === 'initial'" />
              <div
                v-else
                :class="['dot', row.status]"
              />
              <span>{{ $t(versionStatus[row.status]) || '--' }}</span>
            </template>
          </bk-table-column>
          <bk-table-column
            :label="$t('操作')"
            :width="localLanguage === 'en' ? 280 : 200"
          >
            <template slot-scope="{ row }">
              <bk-button
                theme="primary"
                text
                class="mr10"
                @click="handleDetail(row)"
              >
                {{ $t('详情') }}
              </bk-button>
              <bk-button
                theme="primary"
                text
                class="mr10"
                @click="handleRelease(row)"
              >
                {{ $t('发布进度') }}
              </bk-button>
              <bk-button
                v-if="(row.retryable && row.status === 'interrupted') || row.status === 'failed'"
                theme="primary"
                text
                @click="handleRelease(row, 'reset')"
              >
                {{ $t('重新发布') }}
              </bk-button>
            </template>
          </bk-table-column>
        </bk-table>
      </div>
    </paas-content-loader>

    <!-- 详情 -->
    <bk-sideslider
      :is-show.sync="versionDetailConfig.isShow"
      :quick-close="true"
      :width="640"
    >
      <div slot="header">
        {{ $t('版本详情') }}
      </div>
      <div
        slot="content"
        v-bkloading="{ isLoading: versionDetailLoading, opacity: 1 }"
        class="p20"
      >
        <ul :class="['detail-wrapper', { en: localLanguage === 'en' }]">
          <li class="item-info">
            <div class="describe">
              {{ $t('版本号') }}
            </div>
            <div class="content">
              <span class="tag">{{ $t('正式') }}</span>
              {{ versionDetail.version }}
            </div>
          </li>
          <li class="item-info">
            <div class="describe">
              {{ $t('代码库') }}
            </div>
            <div class="content">
              <a
                :href="versionDetail.source_location"
                class="active"
                target="_blank"
              >
                {{ versionDetail.source_location }}
              </a>
            </div>
          </li>
          <li class="item-info">
            <div class="describe">
              {{ $t('代码分支') }}
            </div>
            <div class="content">
              {{ versionDetail.source_version_name }}
            </div>
          </li>
          <li class="item-info">
            <div class="describe">
              {{ $t('版本号类型') }}
            </div>
            <div class="content">
              {{ versionTypeMap[versionDetail.semver_type] }}
            </div>
          </li>
          <li class="item-info h-auto">
            <div class="describe">
              {{ $t('版本日志-label') }}
            </div>
            <div class="content version-log">
              <p>{{ versionDetail.comment }}</p>
            </div>
          </li>
          <li class="item-info">
            <div class="describe">
              {{ $t('发布状态') }}
            </div>
            <div class="content">
              <div class="status-wrapper">
                <round-loading v-if="versionDetail.status === 'pending' || versionDetail.status === 'initial'" />
                <div
                  v-else
                  :class="['dot', versionDetail.status]"
                />
                <span
                  v-bk-tooltips="$t(versionStatus[versionDetail.status])"
                  class="pl5"
                >
                  {{ $t(versionStatus[versionDetail.status]) || '--' }}
                </span>
                <template v-if="versionDetail.status === 'failed'">
                  （{{ $t('部署失败，查看') }}
                  <span
                    class="active"
                    @click="handleRelease(versionDetail)"
                  >
                    {{ $t('详情') }}
                  </span>
                  ）
                </template>
              </div>
            </div>
          </li>
          <li class="item-info">
            <div class="describe">
              {{ $t('发布完成时间') }}
            </div>
            <div class="content">
              {{ versionDetail.complete_time ? formatDate(versionDetail.complete_time) : '--' }}
            </div>
          </li>
        </ul>
      </div>
    </bk-sideslider>
  </div>
</template>

<script>import paasPluginTitle from '@/components/pass-plugin-title';
import pluginBaseMixin from '@/mixins/plugin-base-mixin';
import { PLUGIN_VERSION_STATUS } from '@/common/constants';
import i18n from '@/language/i18n.js';
import { formatDate } from '@/common/tools';
import { clearFilter } from '@/common/utils';

export default {
  components: {
    paasPluginTitle,
  },
  mixins: [pluginBaseMixin],
  data() {
    // 是否根据version判断
    this.versionTypeMap = {
      major: i18n.t('重大版本'),
      minor: i18n.t('次版本'),
      patch: i18n.t('修正版本'),
    };
    return {
      isLoading: true,
      keyword: '',
      versionList: [],
      versionDetail: {},
      isTableLoading: false,
      pagination: {
        current: 1,
        count: 0,
        limit: 10,
      },
      versionDetailConfig: {
        isShow: false,
      },
      versionDetailLoading: true,
      versionStatus: PLUGIN_VERSION_STATUS,
      filterCreator: '',
      filterStatus: '',
      curIsPending: '',
      formatDate,
      isPluginAccessEntry: true,
      pluginDefaultInfo: {
        exposed_link: '',
      },
      tableEmptyConf: {
        keyword: '',
        isAbnormal: false,
      },
      // 插件访问入口禁用
      isAccessDisabled: false,
      accessDisabledTips: '',
    };
  },
  computed: {
    statusFilters() {
      const statusList = [];
      for (const key in this.versionStatus) {
        statusList.push({
          value: key,
          text: this.$t(this.versionStatus[key]),
        });
      }
      return statusList;
    },
    localLanguage() {
      return this.$store.state.localLanguage;
    },
  },
  watch: {
    $route() {
      this.init();
    },
    keyword(newVal, oldVal) {
      if (oldVal && !newVal) {
        this.handleSearch();
      }
    },
    filterStatus() {
      this.getVersionList();
    },
    filterCreator() {
      this.getVersionList();
    },
  },
  created() {
    this.init();
  },
  methods: {
    init() {
      this.getVersionList();
      if (this.pluginFeatureFlags.SHOW_ENTRANCES_ADDRESS) {
        this.getPluginAccessEntry();
      }
    },

    // 切换表格每页显示条数
    limitChange(limit) {
      this.pagination.limit = limit;
      this.pagination.current = 1;
      this.getVersionList(this.pagination.current);
    },

    // 切换分页时会触发的事件
    pageChange(newPage) {
      this.pagination.current = newPage;
      this.getVersionList(newPage);
    },

    // 获取版本列表
    async getVersionList(page = 1) {
      this.isTableLoading = true;
      const curPage = page || this.pagination.current;
      const pageParams = {
        order_by: '-created',
        search_term: this.keyword,
        limit: this.pagination.limit,
        offset: this.pagination.limit * (curPage - 1),
      };
      if (this.filterCreator) {
        pageParams.creator = this.filterCreator;
      }
      // 选择发布中直接传递 status=pending&status=inital
      let statusParams = '';
      if (this.filterStatus.length) {
        // pageParams.status = this.filterStatus;
        let paramsText = '';
        this.filterStatus.forEach((item) => {
          if (item === 'pending') {
            paramsText += 'status=pending&status=initial&';
          } else {
            paramsText += `status=${item}&`;
          }
        });
        statusParams = paramsText.substring(0, paramsText.length - 1);
      }
      this.isDataLoading = true;
      const data = {
        pdId: this.pdId,
        pluginId: this.pluginId,
      };
      try {
        const res = await this.$store.dispatch('plugin/getVersionsManagerList', {
          data,
          pageParams,
          statusParams,
        });
        this.versionList = res.results;
        this.pagination.count = res.count;
        // 当前是否已有任务进行中
        this.curIsPending = this.versionList.find(item => item.status === 'pending');
        this.updateTableEmptyConfig();
        this.tableEmptyConf.isAbnormal = false;
      } catch (e) {
        this.tableEmptyConf.isAbnormal = true;
        this.$bkMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      } finally {
        setTimeout(() => {
          this.isTableLoading = false;
          this.isLoading = false;
        }, 200);
      }
    },

    // 获取版本详情
    async getReleaseDetail(curData) {
      const data = {
        pdId: this.pdId,
        pluginId: this.pluginId,
        releaseId: curData.id,
      };
      try {
        const res = await this.$store.dispatch('plugin/getReleaseDetail', data);
        this.versionDetail = res;
      } catch (e) {
        this.$bkMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      } finally {
        setTimeout(() => {
          this.versionDetailLoading = false;
        }, 300);
      }
    },

    handleFilterChange(filters) {
      if (filters.status) {
        this.filterStatus = filters.status.length ? filters.status : [];
      }

      if (filters.creator) {
        this.filterCreator = filters.creator[0] ? filters.creator[0] : '';
      }
    },

    handleCreateVersion(difference) {
      // 正式版 / 测试版
      // formal / test
      this.$router.push({
        name: 'pluginVersionEditor',
        params: {
          pluginTypeId: this.pdId,
          id: this.pluginId,
        },
        query: {
          isPending: this.curIsPending,
        },
      });
    },

    // 根据关键字搜索
    handleSearch() {
      this.pagination.count = 0;
      this.getVersionList();
    },

    handleDetail(row) {
      this.versionDetailConfig.isShow = true;
      this.versionDetailLoading = true;
      this.getReleaseDetail(row);
    },

    // 发布
    handleRelease(data, isReset) {
      if (isReset) {
        this.republish(data);
      } else {
        this.$router.push({
          name: 'pluginVersionRelease',
          query: {
            release_id: data.id,
          },
        });
      }
    },

    // 重新发布前状态
    async republish(data) {
      const params = {
        pdId: this.pdId,
        pluginId: this.pluginId,
        releaseId: data.id,
      };
      try {
        const res = await this.$store.dispatch('plugin/republishRelease', params);
        this.$router.push({
          name: 'pluginVersionRelease',
          query: {
            stage_id: res.current_stage && res.current_stage.stage_id,
            release_id: data.id,
          },
        });
      } catch (e) {
        this.$bkMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      } finally {
        setTimeout(() => {
          this.isLoading = false;
        }, 200);
      }
    },
    clearFilterKey() {
      this.keyword = '';
      this.$refs.versionTable.clearFilter();
      if (this.$refs.versionTable.$refs.tableHeader) {
        const { tableHeader } = this.$refs.versionTable.$refs;
        clearFilter(tableHeader);
      }
    },
    // 获取访问入口链接
    async getPluginAccessEntry() {
      try {
        const res = await this.$store.dispatch('plugin/getPluginAccessEntry', {
          pluginId: this.pluginId,
        });
        this.pluginDefaultInfo = res;
        this.isAccessDisabled = false;
      } catch (e) {
        this.isAccessDisabled = true;
        this.accessDisabledTips = e.detail || e.message || this.$t('接口异常');
      }
    },
    handleOpenLink() {
      if (this.isPluginAccessEntry) {
        window.open(this.pluginDefaultInfo.exposed_link.url, '_blank');
      }
    },

    updateTableEmptyConfig() {
      if (this.keyword || this.filterStatus.length || this.filterCreator.length) {
        this.tableEmptyConf.keyword = 'placeholder';
        return;
      }
      this.tableEmptyConf.keyword = '';
    },
  },
};
</script>

<style lang="scss" scoped>
.ps-main {
  margin-top: 15px;
}
.plugin-top-title {
  margin-top: 12px;
}
.app-container {
  padding-top: 2px;
}
.header-title {
  margin: 16px 0;
  max-width: 980px;
  display: flex;
  align-items: center;
  font-size: 16px;
  color: #313238;
  .app-code {
    color: #979ba5;
  }
  .arrows {
    margin: 0 9px;
    transform: rotate(-90deg);
    font-size: 12px;
    font-weight: 600;
    color: #979ba5;
  }
}

.ag-top-header {
  margin-top: 16px;
}

.ps-version-list {
  margin-top: 22px;

  .version-num {
    color: #3a84ff;
    font-weight: 700;
  }
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
  margin-right: 3px;
}
// .successful {
//     background: #E5F6EA;
//     border: 1px solid #3FC06D;
// }

.successful {
  background: #e5f6ea;
  border: 1px solid #3fc06d;
}

.failed,
.interrupted {
  background: #ffe6e6;
  border: 1px solid #ea3636;
}

.tag {
  border-radius: 2px;
  display: inline-block;
  padding: 3px 8px;

  &.success {
    color: #14a568;
    background: #e4faf0;
  }

  &.danger {
    color: #fe9c00;
    background: #fff1db;
  }

  &.warning {
    background: #ffe8c3;
  }
}

.detail-wrapper {
  &.en {
    .item-info .describe {
      width: 150px;
    }
  }
  .item-info {
    display: flex;
    height: 40px;
    line-height: 40px;
    border-top: 1px solid #dfe0e5;

    &:last-child {
      border-bottom: 1px solid #dfe0e5;
    }

    .describe,
    .content {
      display: flex;
      align-items: center;
    }

    .version-log {
      display: block;
    }

    .describe {
      flex-direction: row-reverse;
      width: 130px;
      text-align: right;
      padding-right: 16px;
      font-size: 12px;
      color: #979ba5;
      line-height: normal;
      background: #fafbfd;
    }
    .content {
      flex: 1;
      font-size: 12px;
      color: #63656e;
      padding: 10px 0 10px 16px;
      border-left: 1px solid #f0f1f5;
    }
    .status-wrapper {
      display: flex;
      align-items: center;
    }
    .active {
      color: #3a84ff;
      cursor: pointer;
    }
    .tag {
      display: inline-block;
      padding: 0 3px;
      font-size: 12px;
      height: 16px;
      line-height: 16px;
      background: #64baa1;
      border-radius: 2px;
      color: #fff;
      margin-right: 5px;
    }
  }

  .h-auto {
    height: auto;
    line-height: 22px;
  }
}
.empty-tips {
  margin-top: 5px;
  color: #979ba5;
  .clear-search {
    cursor: pointer;
    color: #3a84ff;
  }
}
</style>

<style>
.biz-create-success .bk-table th .bk-table-column-filter-trigger.is-filtered {
  color: #3a84ff !important;
}
</style>
