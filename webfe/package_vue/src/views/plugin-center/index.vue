<template>
  <div class="bk-plugin-wrapper mt30 right-main-plugin">
    <paas-content-loader
      :is-loading="loading"
      placeholder="pluin-list-loading"
      offset-top="20"
      class="wrap"
      :height="575"
    >
      <div class="paas-plugin-tit">
        <h3> {{ $t('我的插件') }}</h3>
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
          :placeholder="$t('输入插件ID、插件名称，按Enter搜索')"
          :clearable="true"
          :right-icon="'paasng-icon paasng-search'"
          @enter="handleSearch"
        />
      </div>
      <bk-table
        ref="pluginTable"
        v-bkloading="{ isLoading: isDataLoading }"
        :data="pluginList"
        size="small"
        ext-cls="plugin-list-table"
        :pagination="pagination"
        :outer-border="false"
        :header-border="false"
        :show-overflow-tooltip="true"
        @page-limit-change="handlePageLimitChange"
        @page-change="handlePageChange"
        @filter-change="handleFilterChange"
      >
        <div
          v-if="isSearchClear || pluginList.length || filterKey"
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
        <bk-table-column :label="$t('插件 ID')">
          <template slot-scope="{ row }">
            <img
              :src="row.logo"
              onerror="this.src='/static/images/plugin-default.svg'"
              class="plugin-logo-cls"
            >
            <bk-button
              v-bk-tooltips="row.id"
              text
              @click="toPluginSummary(row)"
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
          :filter-multiple="true"
        >
          <template slot-scope="{ row }">
            {{ row.pd_name || '--' }}
          </template>
        </bk-table-column>
        <bk-table-column
          :label="$t('创建时间')"
          prop="created"
          sortable
        >
          <template slot-scope="{ row }">
            {{ row.created || '--' }}
          </template>
        </bk-table-column>
        <bk-table-column
          :label="$t('开发语言')"
          prop="language"
          column-key="language"
          :filters="languageFilters"
          :filter-multiple="true"
        />
        <bk-table-column
          :label="$t('版本')"
        >
          <template slot-scope="{ row }">
            <template
              v-if="row.latest_release"
            >
              <round-loading v-if="releaseStatusMap[row.latest_release.status]" />
              <div
                v-else
                :class="['dot', row.latest_release.status]"
              />
              {{ row.latest_release.version }}
            </template>
            <template
              v-else
            >
              --
            </template>
          </template>
        </bk-table-column>
        <bk-table-column
          :label="$t('操作')"
          :width="localLanguage === 'en' ? 280 : 200"
        >
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
                  {{ row.ongoing_release && releaseStatusMap[row.ongoing_release.status] ? $t('发布进度') : $t('发布') }}
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
      :title="$t('确定删除插件')"
      :theme="'primary'"
      :mask-close="false"
      :loading="removePluginDialog.isLoading"
      @confirm="handlerDeletePlugin"
    >
      <div>
        {{ $t('是否确定删除') }} {{ removePluginDialog.selectedPlugin.id }}
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
                filterLanguage: [],
                filterPdName: [],
                languageFilters: [],
                pluginTypeFilters: [],
                removePluginDialog: {
                    visiable: false,
                    isLoading: false,
                    selectedPlugin: {}
                },
                releaseStatusMap: {
                    'pending': 'pending',
                    'initial': 'initial'
                },
                isSearchClear: false
            };
        },
        computed: {
            localLanguage () {
                return this.$store.state.localLanguage;
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
                        order_by: 'id',
                        search_term: this.filterKey
                    };
                    let statusParams = '';
                    let languageParams = '';
                    let pdIdParams = '';
                    if (this.filterLanguage.length) {
                        // pageParams.language = this.filterLanguage;
                        let paramsText = '';
                        this.filterLanguage.forEach(item => {
                            paramsText += `language=${item}&`;
                        });
                        languageParams = paramsText.substring(0, paramsText.length - 1);
                    }
                    if (this.filterPdName.length) {
                        // pageParams.pd__identifier = this.filterPdName;
                        let paramsText = '';
                        this.filterPdName.forEach(item => {
                            paramsText += `pd__identifier=${item}&`;
                        });
                        pdIdParams = paramsText.substring(0, paramsText.length - 1);
                    }
                    this.isDataLoading = true;
                    const res = await this.$store.dispatch('plugin/getPlugins', {
                        pageParams,
                        statusParams,
                        languageParams,
                        pdIdParams
                    });
                    this.pluginList = res.results;
                    this.pagination.count = res.count;
                } catch (e) {
                    this.$paasMessage({
                        limit: 1,
                        theme: 'error',
                        message: e.message
                    });
                } finally {
                    this.isDataLoading = false;
                    this.loading = false;
                    this.isSearchClear = false;
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
                this.removePluginDialog.selectedPlugin = row;
            },

            async handlerDeletePlugin () {
                try {
                    this.removePluginDialog.isLoading = true;
                    await this.$store.dispatch('plugin/deletePlugin', {
                        pdId: this.removePluginDialog.selectedPlugin.pd_id,
                        pluginId: this.removePluginDialog.selectedPlugin.id
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
                if (filters.language) {
                    this.filterLanguage = filters.language.length ? filters.language : [];
                }

                if (filters.pd_name) {
                    this.filterPdName = filters.pd_name.length ? filters.pd_name : [];
                }
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
                if (data.ongoing_release && this.releaseStatusMap[data.ongoing_release.status]) {
                    this.$router.push({
                        name: 'pluginVersionRelease',
                        params: { pluginTypeId: data.pd_id, id: data.id },
                        query: {
                            release_id: data.ongoing_release.id
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
            },

            clearFilterKey () {
                // 防止清空搜索条件时提示抖动
                this.isSearchClear = true;
                this.filterKey = '';
                this.$refs.pluginTable.clearFilter();
            }
        }
    };
</script>

<style lang="scss" scoped>
    .bk-plugin-wrapper {
        width: 100%;
        padding: 28px 0 44px;
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

        .paas-plugin-input{
            width: 480px;
        }

        .plugin-list-table{
            margin-top: 16px;
            min-height: 600px;
            .point{
                height: 8px;
                width: 8px;
                display: inline-block;
                border-radius: 50%;
                margin-right: 3px;
                border: 1px solid #FF9C01;
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
            .dot.successful {
                background: #E5F6EA;
                border: 1px solid #3FC06D;
            }

            .dot.failed,
            .dot.interrupted {
                background: #FFE6E6;
                border: 1px solid #EA3636;
            }
        }

        .bk-button-text.bk-button-small {
            padding: 0 3px;
            line-height: 26px;
        }
    }
    .wrap {
        width: calc(100% - 120px)
    }
    .plugin-logo-cls {
        width: 16px;
        vertical-align: middle;
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
    .bk-plugin-wrapper .bk-table th .bk-table-column-filter-trigger.is-filtered {
        color: #3a84ff !important;
    }
</style>
