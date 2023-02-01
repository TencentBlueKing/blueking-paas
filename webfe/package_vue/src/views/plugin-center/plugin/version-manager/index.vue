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
            style="display: inline-block;"
          >
            <bk-button
              theme="primary"
              class="mr10"
              :disabled="curIsPending ? true : false"
              @click="handleCreateVersion('formal')"
            >
              {{ $t('新建版本') }}
            </bk-button>
          </div>
          <bk-button
            v-if="pluginFeatureFlags.SHOW_ENTRANCES_ADDRESS && isPluginAccessEntry"
            text
            theme="primary"
            @click="handleOpenLink"
          >
            {{ $t('插件访问入口') }}
            <i class="paasng-icon paasng-jump-link icon-cls-link mr5 copy-text" />
          </bk-button>
          <bk-input
            v-model="keyword"
            class="fr"
            :clearable="true"
            :placeholder="$t('版本号、代码分支')"
            :right-icon="'bk-icon icon-search'"
            style="width: 480px;"
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
          <div
            v-if="versionList.length"
            slot="empty"
          >
            <bk-exception
              class="exception-wrap-item exception-part"
              type="search-empty"
              scene="part"
            />
            <div class="empty-tips">
              {{ $t('可以尝试调整关键词 或') }}
              <span
                class="clear-search"
                @click="clearFilterKey"
              >{{ $t('清空搜索条件') }}</span>
            </div>
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
                style="cursor: pointer;"
                @click="handleDetail(row)"
              >{{ row.version || '--' }}</span>
            </template>
          </bk-table-column>
          <bk-table-column
            :label="$t('代码分支')"
            prop="source_version_name"
          >
            <template slot-scope="{ row }">
              <span>{{ row.source_version_name || '--' }}</span>
            </template>
          </bk-table-column>
          <bk-table-column
            :label="$t('代码 Commit')"
            prop="comment"
          >
            <template slot-scope="{ row }">
              <span>{{ row.source_hash || '--' }}</span>
            </template>
          </bk-table-column>
          <bk-table-column
            :label="$t('创建人')"
            prop="creator"
          >
            <template slot-scope="{ row }">
              <span>{{ row.creator || '--' }}</span>
            </template>
          </bk-table-column>
          <bk-table-column
            :label="$t('创建时间')"
            prop="created"
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
            width="220"
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
                v-if="row.retryable && row.status === 'interrupted' || row.status === 'failed'"
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
        <ul class="detail-wrapper">
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
              >{{ versionDetail.source_location }}</a>
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
              {{ $t('版本日志') }}
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
                >{{ $t(versionStatus[versionDetail.status]) || '--' }}</span>
                <template v-if="versionDetail.status === 'failed'">
                  （{{ $t('部署失败，查看') }} <span
                    class="active"
                    @click="handleRelease(versionDetail)"
                  >{{ $t('详情') }}</span>）
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

<script>
    import paasPluginTitle from '@/components/pass-plugin-title';
    import pluginBaseMixin from '@/mixins/plugin-base-mixin';
    import { PLUGIN_VERSION_STATUS } from '@/common/constants';
    import i18n from '@/language/i18n.js';
    import { formatDate } from '@/common/tools';

    const PLUGIN_VERSION_STATUS_FILTER = {
        'successful': i18n.t('已上线'),
        'failed': i18n.t('失败'),
        'pending': i18n.t('发布中'),
        'interrupted': i18n.t('已中断')
    };

    export default {
        components: {
            paasPluginTitle
        },
        mixins: [pluginBaseMixin],
        data () {
            // 是否根据version判断
            this.versionTypeMap = {
                major: i18n.t('重大版本'),
                minor: i18n.t('次版本'),
                patch: i18n.t('修正版本')
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
                    limit: 10
                },
                versionDetailConfig: {
                    isShow: false
                },
                versionDetailLoading: true,
                versionStatus: PLUGIN_VERSION_STATUS,
                filterCreator: '',
                filterStatus: '',
                curIsPending: '',
                statusFilter: PLUGIN_VERSION_STATUS_FILTER,
                formatDate,
                isPluginAccessEntry: true,
                pluginDefaultInfo: {
                    exposed_link: ''
                }
            };
        },
        computed: {
            statusFilters () {
                const statusList = [];
                for (const key in this.statusFilter) {
                    statusList.push({
                        value: key,
                        text: this.statusFilter[key]
                    });
                }
                return statusList;
            }
        },
        watch: {
            '$route' () {
                this.init();
            },
            keyword (newVal, oldVal) {
                if (oldVal && !newVal) {
                    this.handleSearch();
                }
            },
            filterStatus () {
                this.getVersionList();
            },
            filterCreator () {
                this.getVersionList();
            }
        },
        created () {
            this.init();
        },
        methods: {
            init () {
                this.getVersionList();
                this.getPluginAccessEntry();
            },

            // 切换表格每页显示条数
            limitChange (limit) {
                this.pagination.limit = limit;
                this.pagination.current = 1;
                this.getVersionList(this.pagination.current);
            },

            // 切换分页时会触发的事件
            pageChange (newPage) {
                this.pagination.current = newPage;
                this.getVersionList(newPage);
            },

            // 获取版本列表
            async getVersionList (page = 1) {
                this.isTableLoading = true;
                const curPage = page || this.pagination.current;
                const pageParams = {
                    order_by: '-created',
                    search_term: this.keyword,
                    limit: this.pagination.limit,
                    offset: this.pagination.limit * (curPage - 1)
                };
                if (this.filterCreator) {
                    pageParams.creator = this.filterCreator;
              }
                // 选择发布中直接传递 status=pending&status=inital
                let statusParams = '';
                if (this.filterStatus.length) {
                    // pageParams.status = this.filterStatus;
                    let paramsText = '';
                    this.filterStatus.forEach(item => {
                        if (item === 'pending') {
                            paramsText += `status=pending&status=initial&`;
                        } else {
                            paramsText += `status=${item}&`;
                        }
                    });
                    statusParams = paramsText.substring(0, paramsText.length - 1);
                }
                this.isDataLoading = true;
                const data = {
                    pdId: this.pdId,
                    pluginId: this.pluginId
                };
                try {
                    const res = await this.$store.dispatch('plugin/getVersionsManagerList', {
                      data,
                      pageParams,
                      statusParams
                    });
                    this.versionList = res.results;
                    this.pagination.count = res.count;
                    // 当前是否已有任务进行中
                    this.curIsPending = this.versionList.find(item => item.status === 'pending');
                } catch (e) {
                    this.$bkMessage({
                        theme: 'error',
                        message: e.detail || e.message || this.$t('接口异常')
                    });
                } finally {
                    setTimeout(() => {
                        this.isTableLoading = false;
                        this.isLoading = false;
                    }, 200);
                }
            },

            // 获取版本详情
            async getReleaseDetail (curData) {
                const data = {
                    pdId: this.pdId,
                    pluginId: this.pluginId,
                    releaseId: curData.id
                };
                try {
                    const res = await this.$store.dispatch('plugin/getReleaseDetail', data);
                    this.versionDetail = res;
                } catch (e) {
                    this.$bkMessage({
                        theme: 'error',
                        message: e.detail || e.message || this.$t('接口异常')
                    });
                } finally {
                    setTimeout(() => {
                        this.versionDetailLoading = false;
                    }, 300);
                }
            },

            handleFilterChange (filters) {
                if (filters.status) {
                    this.filterStatus = filters.status.length ? filters.status : [];
                }

                if (filters.creator) {
                    this.filterCreator = filters.creator[0] ? filters.creator[0] : '';
                }
            },

            handleCreateVersion (difference) {
                // 正式版 / 测试版
                // formal / test
                this.$router.push({
                    name: 'pluginVersionEditor',
                    params: {
                        pluginTypeId: this.pdId,
                        id: this.pluginId
                    },
                    query: {
                        isPending: this.curIsPending
                    }
                });
            },

            // 根据关键字搜索
            handleSearch () {
                this.pagination.count = 0;
                this.getVersionList();
            },

            handleDetail (row) {
                this.versionDetailConfig.isShow = true;
                this.versionDetailLoading = true;
                this.getReleaseDetail(row);
            },

            // 发布
            handleRelease (data, isReset) {
                const stagesData = data.all_stages.map((e, i) => {
                    e.icon = i + 1;
                    e.title = e.name;
                    return e;
                });
                this.$store.commit('plugin/updateStagesData', stagesData);
                if (isReset) {
                  this.republish(data);
                } else {
                  this.$router.push({
                      name: 'pluginVersionRelease',
                      query: {
                          stage_id: data.current_stage.stage_id,
                          release_id: data.id
                      }
                  });
                }
            },

            // 重新发布前状态
            async republish (data) {
                const params = {
                    pdId: this.pdId,
                    pluginId: this.pluginId,
                    releaseId: data.id
                };
                try {
                    const res = await this.$store.dispatch('plugin/republishRelease', params);
                    this.$router.push({
                      name: 'pluginVersionRelease',
                      query: {
                          stage_id: res.current_stage && res.current_stage.stage_id,
                          release_id: data.id
                      }
                  });
                } catch (e) {
                    this.$bkMessage({
                        theme: 'error',
                        message: e.detail || e.message || this.$t('接口异常')
                    });
                } finally {
                    setTimeout(() => {
                        this.isLoading = false;
                    }, 200);
                }
            },
            clearFilterKey () {
                this.keyword = '';
                this.$refs.versionTable.clearFilter();
            },
            async getPluginAccessEntry () {
                try {
                    const res = await this.$store.dispatch('plugin/getPluginAccessEntry', {
                        pluginId: this.pluginId
                    });
                    this.pluginDefaultInfo = res;
                } catch (e) {
                    // 接口error不展示插件访问入口
                    this.isPluginAccessEntry = false;
                }
            },
            handleOpenLink () {
                if (this.isPluginAccessEntry) {
                    window.open(this.pluginDefaultInfo.exposed_link.url, '_blank');
                }
            }
        }
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
            color: #979BA5;
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
            color: #3A84FF;
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
        background: #E5F6EA;
        border: 1px solid #3FC06D;
    }

    .failed,
    .interrupted {
        background: #FFE6E6;
        border: 1px solid #EA3636;
    }

    .tag {
        border-radius: 2px;
        display: inline-block;
        padding: 3px 8px;

        &.success {
            color: #14A568;
            background: #E4FAF0;
        }

        &.danger {
            color: #FE9C00;
            background: #FFF1DB;
        }

        &.warning {
            background: #FFE8C3;
        }
    }

    .detail-wrapper {
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
                color: #979BA5;
                background: #FAFBFD;
            }
            .content {
                flex: 1;
                font-size: 12px;
                color: #63656E;
                padding: 10px 0 10px 16px;
                border-left: 1px solid #F0F1F5;
            }
            .status-wrapper {
                display: flex;
                align-items: center;
            }
            .active {
                color: #3A84FF;
                cursor: pointer;
            }
            .tag {
                display: inline-block;
                padding: 0 3px;
                font-size: 12px;
                height: 16px;
                line-height: 16px;
                background: #64BAA1;
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
        color: #979BA5;
        .clear-search {
            cursor: pointer;
            color: #3a84ff;
        }
    }
</style>

<style>
    .bk-plugin-wrapper .exception-wrap-item .bk-exception-img.part-img {
        height: 130px;
    }
    .biz-create-success .bk-table th .bk-table-column-filter-trigger.is-filtered {
        color: #3a84ff !important;
    }
</style>
