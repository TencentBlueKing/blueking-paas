<template>
  <div class="bk-plugin-wrapper mt30">
    <paas-content-loader
      :is-loading="loading"
      :placeholder="loaderPlaceholder"
      offset-top="20"
      class="wrap"
      :height="575"
    >
      <div class="paas-plugin-tit">
        <h2> {{ $t('我的插件') }}</h2>
      </div>
      <div class="flex-row justify-content-between">
        <bk-button
          theme="primary"
          @click="createPlugin"
        >
          {{ $t('创建插件') }}
        </bk-button>
        <bk-input
          v-model="filterKey"
          class="paas-plugin-input"
          :placeholder="$t('输入插件标识、插件名称，按Enter搜索')"
          :clearable="true"
          :right-icon="'paasng-icon paasng-search'"
          @enter="handleSearch"
        />
      </div>
      <bk-table
        v-bkloading="{ isLoading: isDataLoading }"
        :data="pluginList"
        size="small"
        ext-cls="plugin-list-table mt20"
        :pagination="pagination"
        :outer-border="false"
        :header-border="false"
        @page-limit-change="handlePageLimitChange"
        @page-change="handlePageChange"
        @filter-change="handleFilterChange"
      >
        <bk-table-column :label="$t('插件标识')">
          <template slot-scope="{ row }">
            <img
              :src="row.logo"
              onerror="this.src='/static/images/plugin-default.svg'"
              class="plugin-logo-cls"
            >
            <bk-button
              v-bk-tooltips="row.id"
              text
              @click="toDetail(row)"
            >
              {{ row.id || '--' }}
            </bk-button>
          </template>
        </bk-table-column>
        <bk-table-column :label="$t('插件名称')">
          <template slot-scope="{ row }">
            <span>{{ row.name_zh_cn }}</span>
          </template>
        </bk-table-column>
        <bk-table-column
          :label="$t('插件类型')"
          prop="pd_name"
          column-key="pd_name"
          :filters="pluginTypeFilters"
          :filter-multiple="false"
        >
          <template slot-scope="{ row }">
            <span v-bk-tooltips="row.pd_name">{{ row.pd_name || '--' }}</span>
          </template>
        </bk-table-column>
        <bk-table-column
          :label="$t('开发语言')"
          prop="language"
          column-key="language"
          :filters="languageFilters"
          :filter-multiple="false"
        />
        <bk-table-column
          :label="$t('状态')"
          prop="status"
          column-key="status"
          :filters="statusFilters"
          :filter-multiple="false"
        >
          <template slot-scope="{ row }">
            <round-loading v-if="row.status === 'releasing'" />
            <div
              v-else
              :class="['point', row.status]"
            />
            <span v-bk-tooltips="pluginStatus[row.status]">{{ pluginStatus[row.status] || '--' }}</span>
          </template>
        </bk-table-column>
        <bk-table-column
          :label="$t('版本')"
        >
          <template slot-scope="{ row }">
            <template
              v-if="row.ongoing_release"
            >
              <round-loading v-if="releaseStatusMap[row.ongoing_release.status]" />
              <div
                v-else
                :class="['dot', row.ongoing_release.status]"
              />
              {{ row.ongoing_release.version }}
            </template>
            <template
              v-else
            >
              --
            </template>
          </template>
        </bk-table-column>
        <bk-table-column :label="$t('操作')">
          <template slot-scope="{ row }">
            <div class="table-operate-buttons">
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
                  {{ $t('发布') }}
                </bk-button>
                <bk-button
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
      title="确定删除插件"
      :theme="'primary'"
      :mask-close="false"
      :loading="removePluginDialog.isLoading"
      @confirm="handlerDeletePlugin"
    >
      <div>
        {{ $t('是否确定删除') }} {{ curPluginData.id }}
      </div>
    </bk-dialog>
  </div>
</template>

<script>
    import { PLUGIN_STATUS } from '@/common/constants';
    export default {
        data () {
            return {
                loading: true,
                loaderPlaceholder: 'apps-loading',
                filterKey: '',
                pluginList: [],
                pluginStatus: PLUGIN_STATUS,
                isDataLoading: true,
                pagination: {
                    current: 1,
                    limit: 10,
                    limitList: [5, 10, 20, 50],
                    count: 0
                },
                isFilter: false,
                filterStatus: '',
                filterLanguage: '',
                filterPdName: '',
                languageFilters: [],
                pluginTypeFilters: [],
                removePluginDialog: {
                    visiable: false,
                    isLoading: false
                },
                curPluginData: {},
                releaseStatusMap: {
                    'pending': 'pending',
                    'initial': 'initial'
                }
            };
        },
        computed: {
            statusFilters () {
                const statusList = [];
                for (const key in PLUGIN_STATUS) {
                    statusList.push({
                        value: key,
                        text: PLUGIN_STATUS[key]
                    });
                }
                return statusList;
            }
        },
        watch: {
            filterKey (newVal, oldVal) {
                if (newVal === '' && oldVal !== '') {
                    if (this.isFilter) {
                        this.fetchPluginsList();
                        this.isFilter = false;
                    }
                }
            },
            filterStatus () {
                this.fetchPluginsList();
            },
            filterLanguage () {
                this.fetchPluginsList();
            },
            filterPdName () {
                this.fetchPluginsList();
            }
        },
        mounted () {
            this.fetchPluginsList();
            this.getPluginFilterParams();
        },
        methods: {
            async fetchPluginsList (page = 1) {
                try {
                    const curPage = page || this.pagination.current;
                    const pageParams = {
                        limit: this.pagination.limit,
                        offset: this.pagination.limit * (curPage - 1),
                        search_term: this.filterKey
                    };
                    if (this.filterStatus) {
                        pageParams.status = this.filterStatus;
                    }
                    if (this.filterLanguage) {
                        pageParams.language = this.filterLanguage;
                    }
                    if (this.filterPdName) {
                        pageParams.pd__identifier = this.filterPdName;
                    }
                    this.isDataLoading = true;
                    const res = await this.$store.dispatch('plugin/getPlugins', {
                        pageParams
                    });
                    this.isDataLoading = false;
                    this.loading = false;
                    this.pluginList = res.results;
                    this.pagination.count = res.results.length;
                } catch (e) {
                    this.$paasMessage({
                        limit: 1,
                        theme: 'error',
                        message: e.message
                    });
                }
            },

            async getPluginFilterParams () {
                try {
                    const res = await this.$store.dispatch('plugin/getPluginFilterParams');
                    for (const key in res) {
                        res[key].forEach(value => {
                            if (key === 'languages') {
                                this.languageFilters.push({
                                    value: value,
                                    text: value
                                });
                            }
                            if (key === 'plugin_types') {
                                this.pluginTypeFilters.push({
                                    value: value.id,
                                    text: value.name
                                });
                            }
                        });
                    }
                } catch (e) {
                    this.$bkMessage({
                        theme: 'error',
                        message: e.detail || e.message || this.$t('接口异常')
                    });
                }
            },

            deletePlugin (row) {
                this.removePluginDialog.visiable = true;
                this.curPluginData = row;
            },

            async handlerDeletePlugin () {
                try {
                    this.removePluginDialog.isLoading = true;
                    await this.$store.dispatch('plugin/deletePlugin', {
                        pdId: this.curPluginData.pd_id,
                        pluginId: this.curPluginData.id
                    });
                    this.$bkMessage({
                        theme: 'success',
                        message: this.$t('删除成功！')
                    });
                    this.removePluginDialog.visiable = false;
                    this.fetchPluginsList();
                } catch (e) {
                    this.$bkMessage({
                        theme: 'error',
                        message: e.detail || e.message || this.$t('接口异常')
                    });
                } finally {
                    this.removePluginDialog.isLoading = false;
                }
            },

            handlePageLimitChange (limit) {
                this.pagination.limit = limit;
                this.pagination.current = 1;
                this.fetchPluginsList(this.pagination.current);
            },

            handlePageChange (newPage) {
                this.pagination.current = newPage;
                this.fetchPluginsList(newPage);
            },

            handleFilterChange (filters) {
                if (filters.status) {
                    this.filterStatus = filters.status[0] ? filters.status[0] : '';
                }

                if (filters.language) {
                    this.filterLanguage = filters.language[0] ? filters.language[0] : '';
                }

                if (filters.pd_name) {
                    this.filterPdName = filters.pd_name[0] ? filters.pd_name[0] : '';
                }
                console.log('filters', filters);
            },

            handleSearch () {
                // API 发布
                if (this.filterKey === '') {
                    return;
                }
                this.isFilter = true;
                this.fetchPluginsList();
            },

            createPlugin () {
                this.$router.push({
                    name: 'createPlugin'
                });
            },

            toPluginSummary (data) {
                this.$router.push({
                    name: 'pluginSummary',
                    params: { pluginTypeId: data.pd_id, id: data.id }
                });
            },

            toParticulars (data) {
                if (data.itsm_detail) {
                    window.open(data.itsm_detail.ticket_url, '_blank');
                }
            },

            toNewVersion (data) {
                if (this.releaseStatusMap[data.ongoing_release.status]) {
                    const stagesData = data.ongoing_release.all_stages.map((e, i) => {
                        e.icon = i + 1;
                        e.title = e.name;
                        return e;
                    });
                    const curVersion = `${data.ongoing_release.version} (${data.ongoing_release.source_version_name})`;
                    this.$store.commit('plugin/updateStagesData', stagesData);
                    this.$router.push({
                        name: 'pluginVersionRelease',
                        params: { pluginTypeId: data.pd_id, id: data.id },
                        query: {
                            stage_id: data.ongoing_release.current_stage.stage_id,
                            release_id: data.id,
                            version: curVersion
                        }
                    });
                } else {
                    this.$router.push({
                        name: 'pluginVersionEditor',
                        params: { pluginTypeId: data.pd_id, id: data.id }
                    });
                }
            },

            toDetail (data) {
                this.$router.push({
                    name: 'pluginVersionManager',
                    params: { pluginTypeId: data.pd_id, id: data.id } // pluginTypeId插件类型标识 id插件标识
                });
            }
        }
    };
</script>

<style lang="scss" scoped>
    .bk-plugin-wrapper {
        width: 100%;
        padding: 28px 0 44px;
        .paas-plugin-tit {
            padding: 20px 0;
            color: #666;
            line-height: 36px;
            position: relative;
        }

        .paas-plugin-tit h2 {
            font-size: 18px;
            font-weight: normal;
            display: inline-block;
            color: #313238;
        }

        .paas-plugin-input{
            width: 480px;
        }

        .plugin-list-table{
            min-height: 600px;
            .point{
                height: 8px;
                width: 8px;
                display: inline-block;
                border-radius: 50%;
                margin-right: 3px;
            }
            .waiting-approval{
                background: #FFE8C3;
                border: 1px solid #FF9C01;
            }

            .approval-failed{
                background:#ffeded;
                border-color:#ffdddd;
            }

            .developing{
                background: #F0F1F5;
                border: 1px solid #C4C6CC;
            }

            .released{
                background: #E5F6EA;
                border: 1px solid #3FC06D;
            }
            .failed{
                background:#ffeded;
                border-color:#ffdddd;
            }

            .dot {
                height: 8px;
                width: 8px;
                display: inline-block;
                border-radius: 50%;
                margin-right: 3px;
            }
            .dot.successful{
                background: #3FC06D;
            }
            .dot.failed{
                background: #EA3636;
            }
            .dot.interrupted{
                background: #EA3636;
            }
        }

        .bk-button-text.bk-button-small {
            padding: 0 3px;
            line-height: 26px;
        }
    }
    .wrap {
        width: 1180px;
    }
    .plugin-logo-cls {
        width: 16px;
        vertical-align: middle;
    }
</style>
