<template lang="html">
  <div class="container biz-create-success">
    <!-- <div class="header-title">
            {{ $t('版本管理') }}
        </div> -->
    <paas-content-loader
      class="app-container middle"
      :is-loading="isLoading"
      placeholder="roles-loading"
    >
      <div class="app-container middle">
        <paas-plugin-title />
        <div class="ag-top-header">
          <bk-button
            theme="primary"
            class="mr10"
            @click="handleCreateVersion('formal')"
          >
            <!-- <i class="paasng-icon paasng-plus"></i> -->
            {{ $t('新建版本') }}
          </bk-button>
          <!-- <bk-button theme="default" @click="handleCreateVersion('test')">
                        <i class="paasng-icon paasng-plus"></i>
                        {{ $t('测试版本') }}
                    </bk-button> -->
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
          <bk-table-column
            :label="$t('版本')"
            prop="version"
            :show-overflow-tooltip="true"
          >
            <template slot-scope="{ row }">
              <span
                v-bk-tooltips="row.version"
                :class="{ 'version-num': row.version }"
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
            :filter-multiple="false"
          >
            <template slot-scope="{ row }">
              <round-loading v-if="row.status === 'pending' || row.status === 'initial'" />
              <div
                v-else
                :class="['dot', row.status]"
              />
              <span v-bk-tooltips="versionStatus[row.status]">{{ versionStatus[row.status] || '--' }}</span>
            </template>
          </bk-table-column>
          <!-- <bk-table-column :label="$t('标签')">
                        <template slot-scope="{ row }">
                            <span :class="['tag', { 'success': row.tag === 'stable' }, { 'danger': row.tag === 'beta' }]">{{ row.tag || '--' }}</span>
                        </template>
                    </bk-table-column> -->
          <bk-table-column
            :label="$t('操作')"
            width="150"
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
                v-if="row.status === 'pending' || row.status === 'initial'"
                theme="primary"
                text
                @click="handleRelease(row)"
              >
                {{ $t('发布进度') }}
              </bk-button>
              <bk-button
                v-if="row.status === 'interrupted'"
                theme="primary"
                text
                @click="handleRelease(row, 'republish')"
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
              {{ versionDetail.semver_type }}
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
          <!-- <li class="item-info">
                        <div class="describe">{{ $t('自定义前端') }}</div>
                        <div class="content">--</div>
                    </li>
                    <li class="item-info">
                        <div class="describe">{{ $t('适用Job类型') }}</div>
                        <div class="content">--</div>
                    </li> -->
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
                  v-bk-tooltips="versionStatus[versionDetail.status]"
                  class="pl5"
                >{{ versionStatus[versionDetail.status] || '--' }}</span>
                <template v-if="versionDetail.status === 'failed'">
                  （部署失败，查看 <span
                    class="active"
                    @click="handleRelease(versionDetail)"
                  >详情</span>）
                </template>
              </div>
            </div>
          </li>
        </ul>
      </div>
    </bk-sideslider>
  </div>
</template>

<script>
    import appBaseMixin from '@/mixins/app-base-mixin';
    import paasPluginTitle from '@/components/pass-plugin-title';
    import { PLUGIN_VERSION_STATUS } from '@/common/constants';

    export default {
        components: {
            paasPluginTitle
        },
        mixins: [appBaseMixin],
        data () {
            // 是否根据version判断
            this.versionTypeMap = {
                major: '重大版本',
                minor: '次版本',
                patch: '修正版本'
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
                filterStatus: ''
            };
        },
        computed: {
            curPluginData () {
                return this.$store.state.plugin.pluginData;
            },
            pdId () {
                return this.$route.params.pluginTypeId;
            },
            pluginId () {
                return this.$route.params.id;
            },
            statusFilters () {
                const statusList = [];
                for (const key in this.versionStatus) {
                    statusList.push({
                        value: key,
                        text: this.versionStatus[key]
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
                if (this.filterStatus) {
                    pageParams.status = this.filterStatus;
                }
                this.isDataLoading = true;
                const data = {
                    pdId: this.pdId,
                    pluginId: this.pluginId
                };
                try {
                    const res = await this.$store.dispatch('plugin/getVersionsManagerList', { data, pageParams });
                    this.versionList = res.results;
                    this.pagination.count = res.count;
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
            async getVersionDetail (curData) {
                const data = {
                    pdId: this.pdId,
                    pluginId: this.pluginId,
                    releaseId: curData.id
                };
                try {
                    const res = await this.$store.dispatch('plugin/getVersionDetail', data);
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
                    this.filterStatus = filters.status[0] ? filters.status[0] : '';
                }

                if (filters.creator) {
                    this.filterCreator = filters.creator[0] ? filters.creator[0] : '';
                }
            },

            handleCreateVersion (difference) {
                // 正式版 / 测试版
                // formal / test
                // this.$router.push({
                //     name: 'pluginVersionManager',
                //     params: { pluginTypeId: data.pd_id, id: data.id } // pluginTypeId插件类型标识 id插件标识
                // });
                this.$router.push({
                    name: 'pluginVersionEditor',
                    params: {
                        pluginTypeId: this.pdId,
                        id: this.pluginId
                    }
                });
            },

            handleSearch () {
                // 根据关键字搜索
                this.pagination.count = 0;
                this.getVersionList();
            },

            handleDetail (row) {
                this.versionDetailConfig.isShow = true;
                this.versionDetailLoading = true;
                this.getVersionDetail(row);
            },

            // 发布
            handleRelease (data, isRepublish) {
                const stagesData = data.all_stages.map((e, i) => {
                    e.icon = i + 1;
                    e.title = e.name;
                    return e;
                });
                const curVersion = `${data.version} (${data.source_version_name})`;
                this.$store.commit('plugin/updateStagesData', stagesData);
                this.$router.push({
                    name: 'pluginVersionRelease',
                    query: {
                        stage_id: data.current_stage.stage_id,
                        release_id: data.id,
                        version: curVersion,
                        isRepublish
                    }
                });
            }
        }
    };
</script>

<style lang="scss" scoped>

    .ps-main {
        margin-top: 15px;
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
        background: rgba(165,218,84,0.20);
        border: 1px solid #A5DA54;
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
                width: 100px;
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
</style>
