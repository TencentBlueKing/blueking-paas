<template lang="html">
  <div class="biz-create-success">
    <version-manage-title
      :type="curVersionType"
      :is-show-tab="curPluginInfo.has_test_version"
      @change-type="handlerChangeRouter"
    />
    <paas-content-loader
      class="app-container container"
      style="width: 100%"
      :is-loading="isLoading"
      placeholder="pluin-version-list-Loading"
      :is-transform="false"
    >
      <div class="top-operate-wrapper">
        <section class="left">
          <!-- 真是版本有发布任务，禁用，测试无需限制 -->
          <span v-bk-tooltips.top="{ content: $t('已有发布任务进行中'), disabled: !isNewVersionDisabled }">
            <bk-button
              theme="primary"
              class="mr15"
              :disabled="isNewVersionDisabled"
              @click="handleCreateVersion(isOfficialVersion ? 'prod' : 'test')"
            >
              {{ isOfficialVersion ? $t('新建版本') : $t('新建测试') }}
            </bk-button>
          </span>
          <span
            v-if="isOfficialVersion"
            v-bk-tooltips="{ content: accessDisabledTips, disabled: !isAccessDisabled }"
          >
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
          <!-- 去发布： 版本发布 -> 新建版本的快捷操作 -->
          <bk-button
            v-if="!isOfficialVersion"
            theme="default"
            class="mr15"
            @click="handleCreateVersion('prod')"
          >
            {{ $t('去发布') }}
          </bk-button>
        </section>

        <section class="left">
          <!-- 过滤出我创建的测试版本 -->
          <bk-button
            v-if="!isOfficialVersion"
            theme="default"
            class="mr15"
            :disabled="!versionList.length"
            @click="handleMyInitiatedTest"
          >
            {{ $t('我发起的测试') }}
          </bk-button>
          <bk-input
            v-model="keyword"
            class="fr"
            :clearable="true"
            :placeholder="$t('版本/代码分支')"
            :right-icon="'bk-icon icon-search'"
            :style="{ width: `${isOfficialVersion ? 480 : 300}px` }"
            @enter="handleSearch"
            @right-icon-click="handleSearch"
          />
        </section>
      </div>

      <section v-if="isCodeccEmpty">
        <bk-exception
          class="exception-wrap-cls"
          type="empty"
          scene="part"
        >
          <div class="exception-wrapper">
            <p class="title">{{ $t('暂无版本发布') }}</p>
            <p class="tips">{{ $t('请先完成对默认分支的测试') }}</p>
            <bk-button
              :text="true"
              title="primary"
              size="small"
              @click="handlerChangeRouter('test')"
            >
              {{ $t('前往测试') }}
            </bk-button>
          </div>
        </bk-exception>
      </section>

      <bk-table
        v-else
        ref="versionTable"
        :key="curVersionType"
        v-bkloading="{ isLoading: isTableLoading }"
        class="pugin-version-list"
        :data="versionList"
        :size="'small'"
        :pagination="pagination"
        :show-overflow-tooltip="true"
        @page-limit-change="limitChange"
        @page-change="pageChange"
        @filter-change="handleFilterChange"
      >
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
          show-overflow-tooltip
        >
          <template slot-scope="{ row }">
            {{ row.version || '--' }}
            <span
              v-if="row.gray_status === 'rolled_back'"
              style="color: #c4c6cc"
            >
              ({{ $t('已回滚') }})
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
            <span
              v-bk-tooltips="row.comment"
              class="tips-dashed"
            >
              {{ row.source_hash.slice(0, 8) || '--' }}
            </span>
          </template>
        </bk-table-column>
        <bk-table-column
          :label="$t('创建人')"
          prop="creator"
          show-overflow-tooltip
        >
          <template slot-scope="{ row }">
            <span>{{ row.creator || '--' }}</span>
          </template>
        </bk-table-column>
        <bk-table-column
          :label="$t('创建时间')"
          prop="created"
          show-overflow-tooltip
        >
          <template slot-scope="{ row }">
            <span>{{ row.created || '--' }}</span>
          </template>
        </bk-table-column>
        <bk-table-column
          :label="$t('完成时间')"
          prop="complete_time"
          show-overflow-tooltip
        >
          <template slot-scope="{ row }">
            <span>{{ row.complete_time ? formatDate(row.complete_time) : '--' }}</span>
          </template>
        </bk-table-column>
        <!-- Codecc -->
        <bk-table-column
          v-if="isCodecc"
          :label="$t('发布状态')"
          prop="status"
          column-key="status"
          :filters="codeccStatusFilters"
          :filter-multiple="true"
        >
          <template slot-scope="{ row }">
            <div :class="['dot', row.gray_status]" />
            <span class="status-text">{{ $t(CODECC_RELEASE_STATUS[row.gray_status]) || '--' }}</span>
          </template>
        </bk-table-column>
        <bk-table-column
          v-else
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
            <span class="status-text">{{ $t(curVersionStatus[row.status]) || '--' }}</span>
          </template>
        </bk-table-column>
        <bk-table-column
          :label="$t('操作')"
          :width="localLanguage === 'en' ? 320 : 240"
        >
          <div slot-scope="{ row }">
            <!-- Codecc 灰度审批详情 -->
            <template v-if="row.source_version_type === 'tested_version' && isOfficialVersion">
              <bk-button
                theme="primary"
                text
                class="mr10"
                @click="handleCodeccReleaseDetails(row)"
              >
                {{ $t('详情') }}
              </bk-button>
              <bk-button
                v-if="row.report_url"
                theme="primary"
                text
                class="mr10"
                @click="toReportPage(row, 'gray')"
              >
                {{ $t('灰度报告') }}
              </bk-button>
              <bk-button
                v-if="canTerminateStatus.includes(row.gray_status)"
                theme="primary"
                text
                class="mr10"
                @click="handleCodeccCancelReleases(row)"
              >
                {{ $t('终止发布') }}
              </bk-button>
              <!-- is_rolled_back = true 表示已回滚 -->
              <span
                v-if="row.id === rollbacks[0]?.id"
                v-bk-tooltips="{ content: $t('当前版本已回滚，不可再次回滚'), disabled: !row.is_rolled_back }"
              >
                <bk-button
                  theme="primary"
                  text
                  :disabled="row.is_rolled_back"
                  @click="showRollbackPopup(row)"
                >
                  {{ $t('回滚版本') }}
                </bk-button>
              </span>
            </template>
            <template v-else>
              <span v-if="isOfficialVersion">
                <bk-button
                  theme="primary"
                  text
                  class="mr10"
                  @click="handleRelease(row)"
                >
                  {{ $t('发布进度') }}
                </bk-button>
              </span>
              <bk-button
                v-else
                theme="primary"
                text
                class="mr10"
                @click="handleRelease(row)"
              >
                {{ $t('详情') }}
              </bk-button>
              <bk-button
                v-if="(row.retryable && row.status === 'interrupted') || row.status === 'failed'"
                theme="primary"
                class="mr10"
                text
                @click="handleRelease(row, 'reset')"
              >
                {{ isOfficialVersion ? $t('重新发布') : $t('重新测试') }}
              </bk-button>
              <bk-button
                v-if="row.report_url"
                theme="primary"
                text
                @click="toReportPage(row, 'test')"
              >
                {{ $t('测试报告') }}
              </bk-button>
              <!-- codecc & 测试记录测试成功 -->
              <bk-button
                v-if="showToRelease(row)"
                theme="primary"
                class="ml10"
                text
                @click="handleCreateVersion('prod', row.version)"
              >
                {{ $t('去发布') }}
              </bk-button>
            </template>
          </div>
        </bk-table-column>
      </bk-table>
    </paas-content-loader>
  </div>
</template>

<script>
import pluginBaseMixin from '@/mixins/plugin-base-mixin';
import versionManageTitle from './comps/version-manage-title.vue';
import {
  PLUGIN_VERSION_STATUS,
  VERSION_NUMBER_TYPE,
  PLUGIN_TEST_VERSION_STATUS,
  CODECC_RELEASE_STATUS,
} from '@/common/constants';
import { formatDate } from '@/common/tools';
import { clearFilter } from '@/common/utils';
import auth from '@/auth';

export default {
  components: {
    versionManageTitle,
  },
  mixins: [pluginBaseMixin],
  data() {
    return {
      isLoading: true,
      keyword: '',
      versionList: [],
      isTableLoading: false,
      pagination: {
        current: 1,
        count: 0,
        limit: 10,
      },
      versionNumberType: VERSION_NUMBER_TYPE,
      filterCreator: '',
      filterStatus: [],
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
      curVersionType: 'test',
      user: {},
      CODECC_RELEASE_STATUS,
      rollbacks: [],
      canTerminateStatus: ['gray_approval_in_progress', 'full_approval_in_progress', 'in_gray'],
    };
  },
  computed: {
    statusFilters() {
      return this.formatStatusFilters(this.curVersionStatus);
    },
    codeccStatusFilters() {
      return this.formatStatusFilters(CODECC_RELEASE_STATUS);
    },
    localLanguage() {
      return this.$store.state.localLanguage;
    },
    // 正式版
    isOfficialVersion() {
      return this.curVersionType === 'prod';
    },
    curUserInfo() {
      return this.$store.state.curUserInfo;
    },
    isNewVersionDisabled() {
      return this.isOfficialVersion ? !!this.curIsPending : false;
    },
    // 当前版本状态
    curVersionStatus() {
      return this.isOfficialVersion ? PLUGIN_VERSION_STATUS : PLUGIN_TEST_VERSION_STATUS;
    },
    // Codecc 空状态
    isCodeccEmpty() {
      if (this.filterStatus.length) return false;
      if (!this.versionList.length && this.isCodecc) return true;
      return false;
    },
    isCodecc() {
      return this.curPluginInfo.has_test_version && this.isOfficialVersion;
    },
  },
  watch: {
    $route() {
      this.isLoading = true;
      this.filterCreator = '';
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
      if (!this.curPluginInfo.has_test_version) {
        // 不区分版本
        this.curVersionType = 'prod';
        this.handlerChangeRouter();
      } else {
        this.curVersionType = this.$route.query.type || 'test';
      }
      this.getVersionList();
      this.getReleasedVersion();
      if (this.isCodecc) {
        this.getRollbackVersion();
      }
      // 获取当前用户信息
      if (this.curVersionType === 'test' && !this.curUserInfo.username) {
        this.getCurrentUser();
      }
      if (this.pluginFeatureFlags.SHOW_ENTRANCES_ADDRESS && this.curVersionType === 'prod') {
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

    // 格式化当前插件状态
    formatStatusFilters(data) {
      const statusList = [];
      for (const key in data) {
        statusList.push({
          value: key,
          text: this.$t(data[key]),
        });
      }
      return statusList;
    },

    formatPageParams(page) {
      const curPage = page || this.pagination.current;
      const params = {
        order_by: '-created',
        search_term: this.keyword,
        limit: this.pagination.limit,
        offset: this.pagination.limit * (curPage - 1),
        type: this.curVersionType,
      };
      // 创建人
      if (this.filterCreator) {
        params.creator = this.filterCreator;
      }
      return params;
    },

    // 格式化状态
    formatStatusParams() {
      let statusParams = '';
      if (this.filterStatus.length) {
        const key = this.isCodecc ? 'gray_status' : 'status';
        let paramsText = '';
        this.filterStatus.forEach((item) => {
          // 选择发布中直接传递 status=pending&status=inital
          if (item === 'pending') {
            paramsText += `${key}=pending&${key}=initial&`;
          } else {
            paramsText += `${key}=${item}&`;
          }
        });
        statusParams = paramsText.substring(0, paramsText.length - 1);
      }
      return statusParams;
    },

    // 获取指定状态版本，判断是否有版本正在灰度或者发布中
    async getReleasedVersion() {
      if (!this.isOfficialVersion) return;
      try {
        const res = await this.$store.dispatch('plugin/getVersionsManagerList', {
          data: {
            pdId: this.pdId,
            pluginId: this.pluginId,
          },
          pageParams: { type: 'prod' },
          statusParams: 'status=pending&status=initial',
        });
        // 当前是否已有任务进行中
        this.curIsPending = !!res.results.length;
      } catch (e) {
        console.error(e);
      }
    },

    // 获取版本列表
    async getVersionList(page = 1) {
      this.isTableLoading = true;
      const data = {
        pdId: this.pdId,
        pluginId: this.pluginId,
      };
      const pageParams = this.formatPageParams(page);
      const statusParams = this.formatStatusParams();
      try {
        const res = await this.$store.dispatch('plugin/getVersionsManagerList', {
          data,
          pageParams,
          statusParams,
        });
        this.versionList = res.results;
        this.pagination.count = res.count;
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

    // 获取回滚版本
    async getRollbackVersion() {
      try {
        const res = await this.$store.dispatch('plugin/getVersionsManagerList', {
          data: {
            pdId: this.pdId,
            pluginId: this.pluginId,
          },
          pageParams: {
            order_by: '-created',
            limit: 2,
            offset: 0,
            status: 'successful',
            is_rolled_back: false,
            type: this.curVersionType,
          },
        });
        const { results } = res;
        // 不符合回滚条件
        if (results.length < 2) return;
        this.rollbacks = results;
      } catch (e) {
        this.$bkMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      }
    },

    // 获取当前用户信息
    getCurrentUser() {
      auth.requestCurrentUser().then((user) => {
        this.user = user;
        this.$store.commit('updataUserInfo', user);
      });
    },

    handleFilterChange(filters) {
      if (filters.status) {
        this.filterStatus = filters.status.length ? filters.status : [];
      }

      if (filters.creator) {
        this.filterCreator = filters.creator[0] ? filters.creator[0] : '';
      }
    },

    handleCreateVersion(type, version) {
      // 正式版 / 测试版
      this.$router.push({
        name: 'pluginVersionEditor',
        params: {
          pluginTypeId: this.pdId,
          id: this.pluginId,
        },
        query: {
          isPending: !!this.curIsPending,
          type,
          releaseVersion: version,
        },
      });
    },

    // 根据关键字搜索
    handleSearch() {
      this.pagination.count = 0;
      this.getVersionList();
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
            type: this.curVersionType,
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
            type: this.curVersionType,
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
        // 已下架
        if (res.is_offlined) {
          this.isAccessDisabled = true;
          this.accessDisabledTips = this.$t('该插件已下架。如需继续使用，请创建新版本。');
          return;
        }
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

    handlerChangeRouter(key) {
      const query = {};
      if (key) {
        this.curVersionType = key;
        query.type = key;
      }
      this.$router.push({
        query,
      });
    },

    // 过滤出我发起的测试
    handleMyInitiatedTest() {
      const username = this.curUserInfo.username || this.user.username;
      this.filterCreator = username;
      this.getVersionList();
    },

    // 测试报告
    toReportPage(row, type) {
      let url = `${row.report_url}?currentVersion=${row.version}`;
      if (type === 'gray') {
        url += '&stage=3';
      }
      this.$router.push({
        name: 'pluginTestReport',
        params: {
          pluginTypeId: this.pdId,
          id: this.pluginId,
        },
        query: {
          type: type === 'gray' ? 'prod' : 'test',
          url,
        },
      });
    },

    // Codecc 版本发布详情
    handleCodeccReleaseDetails(row) {
      this.$router.push({
        name: 'pluginReleaseDetails',
        params: {
          pluginTypeId: this.pdId,
          id: this.pluginId,
        },
        query: {
          versionId: row.id,
        },
      });
    },

    // 回滚
    showRollbackPopup(row) {
      if (!this.rollbacks.length) return;
      const h = this.$createElement;
      const rollback = this.rollbacks[1];
      const location = row.source_location.replace(/\.git$/, '');

      this.$bkInfo({
        type: 'warning',
        title: this.$t('确认回滚至上一版本？'),
        subHeader: h('div', [
          this.createVersionInfo(
            this.$t('当前版本'),
            row.version,
            row.source_hash.slice(0, 8),
            `${location}/commit/${row.source_hash}`
          ),
          this.createVersionInfo(
            this.$t('回滚至版本'),
            rollback.version,
            rollback.source_hash.slice(0, 8),
            `${location}/commit/${rollback.source_hash}`
          ),
        ]),
        okText: this.$t('回滚'),
        confirmFn: () => {
          this.handleRollbackVersion(row.id);
        },
      });
    },

    createVersionInfo(label, version, hash, url) {
      const h = this.$createElement;
      const fn = () => {
        window.open(url, '_blank');
      };
      return h('p', [
        h('span', `${label}：`),
        h('span', [
          h('span', { style: { color: '#313238' } }, version),
          h(
            'span',
            {
              class: ['ml8'],
              style: { color: '#3A84FF', cursor: 'pointer' },
              on: {
                click: fn,
              },
            },
            hash
          ),
        ]),
      ]);
    },

    // 回滚版本
    async handleRollbackVersion(id) {
      try {
        await this.$store.dispatch('plugin/versionRollback', {
          pdId: this.pdId,
          pluginId: this.pluginId,
          releaseId: id,
        });
        this.getVersionList();
      } catch (e) {
        this.$bkMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      }
    },

    // 终止发布弹窗
    handleCodeccCancelReleases(row) {
      this.$bkInfo({
        title: `${this.$t('确认终止发布版本')}${row.source_version_name} ？`,
        width: 540,
        maskClose: true,
        confirmLoading: true,
        confirmFn: async () => {
          try {
            await this.$store.dispatch('plugin/codeccCancelReleases', {
              pdId: this.pdId,
              pluginId: this.pluginId,
              releaseId: row.id,
            });
            this.$bkMessage({
              theme: 'success',
              message: this.$t('已终止当前的发布版本'),
            });
            this.getVersionList();
            this.getReleasedVersion();
          } catch (e) {
            this.$bkMessage({
              theme: 'error',
              message: e.detail || e.message || this.$t('接口异常'),
            });
          } finally {
            return true;
          }
        },
      });
    },

    // 是否展示去发布
    showToRelease(row) {
      // 测试成功并且分支为 master，展示去发布快捷入口
      return (
        this.curPluginInfo.has_test_version &&
        !this.isOfficialVersion &&
        row.status === 'successful' &&
        row.source_version_name === 'master'
      );
    },
  },
};
</script>

<style lang="scss" scoped>
.ps-main {
  margin-top: 15px;
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

.pugin-version-list {
  margin-top: 22px;
  background: #fff;

  .status-text {
    margin-left: 5px;
  }
  .tips-dashed {
    border-bottom: 1px dashed;
  }
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
  margin-right: 3px;

  &.successful,
  &.fully_released {
    background: #e5f6ea;
    border: 1px solid #3fc06d;
  }

  &.failed,
  &.interrupted,
  &.full_approval_failed,
  &.gray_approval_failed {
    background: #ffe6e6;
    border: 1px solid #ea3636;
  }
  &.full_approval_in_progress,
  &.gray_approval_in_progress {
    background: #ffe8c3;
    border: 1px solid #ff9c01;
  }
  &.in_gray {
    background: #e1ecff;
    border: 1px solid #699df4;
  }
  &.rolled_back {
    background: #f0f1f5;
    border: 1px solid #dcdee5;
  }
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

.empty-tips {
  margin-top: 5px;
  color: #979ba5;
  .clear-search {
    cursor: pointer;
    color: #3a84ff;
  }
}
.top-operate-wrapper {
  display: flex;
  justify-content: space-between;
  .right {
    display: flex;
  }
}
.biz-create-success {
  .app-container.container {
    padding-top: 16px !important;
  }
  .exception-wrap-cls {
    margin-top: 100px;
    /deep/ .bk-exception-img.part-img .exception-image {
      height: 180px;
    }
    .exception-wrapper {
      .title {
        font-size: 24px;
        color: #63656e;
        margin-bottom: 16px;
      }
      .tips {
        font-size: 14px;
        color: #979ba5;
        margin-bottom: 8px;
      }
    }
  }
}
</style>

<style>
.biz-create-success .bk-table th .bk-table-column-filter-trigger.is-filtered {
  color: #3a84ff !important;
}
</style>
