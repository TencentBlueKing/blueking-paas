<template lang="html">
  <div class="right-main">
    <app-top-bar
      :title="$t('代码检查')"
      :can-create="canCreateModule"
      :cur-module="curAppModule"
      :module-list="curAppModuleList"
    />

    <paas-content-loader
      class="app-container middle"
      :is-loading="isLoading"
      placeholder="code-review-loading"
      :offset-top="30"
    >
      <template v-if="showPage && !isLoading">
        <div v-bkloading="{ isLoading: tableLoading, opacity: 1 }">
          <bk-table
            :data="reviewList"
            size="small"
            :pagination="pagination"
            @page-change="pageChange"
            @page-limit-change="limitChange"
          >
            <div slot="empty">
              <table-empty empty />
            </div>
            <bk-table-column :label="$t('检查版本')">
              <template slot-scope="{ row }">
                <span v-bk-tooltips="row.deployment.repo.revision || ''">{{ row.deployment.repo.revision.substring(0, 8) || '--' }}</span>
              </template>
            </bk-table-column>
            <bk-table-column :label="$t('检查分支')">
              <template slot-scope="{ row }">
                <span>{{ row.deployment.repo.name || '--' }}</span>
              </template>
            </bk-table-column>
            <bk-table-column :label="$t('检查时间')">
              <template slot-scope="{ row }">
                <span>{{ row.created || '--' }}</span>
              </template>
            </bk-table-column>
            <bk-table-column :label="$t('执行状态')">
              <template slot-scope="{ row }">
                <span :style="{ color: computedColor(row.status) }">{{ statusMap[row.status] }}</span>
              </template>
            </bk-table-column>
            <bk-table-column
              :label="$t('检查结果')"
              width="120"
            >
              <template slot-scope="{ row }">
                <bk-button
                  text
                  @click="handleViewDetail(row)"
                >
                  {{ $t('查看详情') }}
                </bk-button>
              </template>
            </bk-table-column>
          </bk-table>
        </div>
        <div class="hlep-docu">
          <label class="label"> {{ $t('帮助文档') }} </label>
          <div style="margin-top: 10px;">
            <bk-button
              text
              style="padding-left: 0;"
              @click="handleCodeDocu"
            >
              {{ $t('代码检查服务说明') }}
            </bk-button>
          </div>
        </div>
      </template>
      <template v-if="!showPage && !isLoading">
        <div class="mt50 tc">
          <span class="paasng-icon paasng-empty warn-icon" />
          <p class="no-git-wrapper">
            {{ $t('该模块暂不支持代码检查功能，可通过') }}
            <bk-button
              text
              style="padding-left: 0;"
              @click="handleCodeDocu"
            >
              {{ $t('代码检查服务说明') }}
            </bk-button>
            {{ $t('了解详情') }}
          </p>
        </div>
      </template>
    </paas-content-loader>
  </div>
</template>

<script>
    import appBaseMixin from '@/mixins/app-base-mixin';
    import appTopBar from '@/components/paas-app-bar';

    export default {
        components: {
            appTopBar
        },
        mixins: [appBaseMixin],
        data () {
            return {
                isLoading: true,
                tableLoading: false,
                reviewList: [],
                envVal: 'all',
                pagination: {
                    current: 1,
                    count: 0,
                    limit: 10
                },
                envMap: {
                    'prod': this.$t('生产环境'),
                    'stag': this.$t('预发布环境')
                },
                statusMap: {
                    'successful': this.$t('成功'),
                    'failed': this.$t('失败'),
                    'pending': this.$t('进行中')
                },
                currentBackup: 1,
                showPage: true,
                requestQueue: ['ci', 'list']
            };
        },
        watch: {
            '$route' () {
                this.envVal = 'all';
                this.isLoading = true;
                this.requestQueue = ['ci', 'list'];
                this.init();
            },
            // 'pagination.current' (value) {
            //     this.currentBackup = value
            // },
            requestQueue (value) {
                if (!value.length) {
                    this.isLoading = false;
                }
            }
        },
        created () {
            this.init();
        },
        methods: {
            async init () {
                await this.fetchCiInfo();
                await this.fetchCodeReviewList(false);
            },
            computedColor (status) {
                const colorMap = {
                    'successful': '#5bd18b',
                    'failed': '#ff5656',
                    'pending': '#ffb400'
                };
                return colorMap[status];
            },
            async fetchCiInfo () {
                try {
                    const res = await this.$store.dispatch('devopsAuth/getCiInfo', {
                        appCode: this.appCode,
                        moduleId: this.curModuleId
                    });
                    this.showPage = res.enabled;
                } catch (e) {
                    this.$paasMessage({
                        limit: 1,
                        theme: 'error',
                        message: e.message
                    });
                } finally {
                    this.requestQueue.shift();
                }
            },
            // isTableLoadingFlag 为 false 时
            async fetchCodeReviewList (isTableLoadingFlag = true) {
                if (isTableLoadingFlag) {
                    this.tableLoading = true;
                }
                try {
                    const res = await this.$store.dispatch('devopsAuth/getCodeReviewList', {
                        appCode: this.appCode,
                        moduleId: this.curModuleId,
                        limit: this.pagination.limit,
                        offset: (this.currentBackup - 1) * this.pagination.limit,
                        env: this.envVal === 'all' ? '' : this.envVal
                    });
                    this.reviewList = res.results || [];
                    this.pagination.count = res.count || 0;
                } catch (e) {
                    this.$paasMessage({
                        theme: 'error',
                        message: e.detail || this.$t('接口异常')
                    });
                } finally {
                    this.tableLoading = false;
                    this.requestQueue.shift();
                }
            },
            filterCodeReviewByEnv (value) {
                this.envVal = value;
                this.fetchCodeReviewList();
            },
            handleViewDetail (data) {
                window.open(data.detail.url);
            },
            handleCodeDocu () {
                window.open(this.GLOBAL.DOC.CODE_REVIEW);
            },
            pageChange (page) {
                // 点击当前页不请求接口
                if (this.currentBackup === page) {
                    return;
                }
                this.pagination.current = page;
                this.currentBackup = page;
                this.fetchCodeReviewList();
            },

            limitChange (currentLimit, prevLimit) {
                this.pagination.limit = currentLimit;
                this.pagination.current = 1;
                this.currentBackup = 1;
                this.fetchCodeReviewList();
            }
        }
    };
</script>

<style lang="scss" scoped>
    .app-container {
        padding-top: 11px;
    }
    .warn-icon {
        font-size: 40px;
        color: rgb(255, 195, 73);
        text-align: center;
    }
    .no-git-wrapper {
        margin-top: 10px;
        text-align: center;
    }
    .hlep-docu {
        margin-top: 20px;
        .label {
            color: #55545a;
            font-weight: 600;
        }
    }
</style>
