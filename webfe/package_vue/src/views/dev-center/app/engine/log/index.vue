<template lang="html">
  <div
    :key="appCode"
    class="right-main"
  >
    <app-top-bar
      :title="$t('日志查询')"
      :can-create="canCreateModule"
      :cur-module="curAppModule"
      :module-list="curAppModuleList"
    />

    <paas-content-loader
      class="app-container log-middle"
      :is-loading="isLoading"
      placeholder="log-loading"
      :offset-top="60"
    >
      <section>
        <bk-tab
          :active.sync="tabActive"
          type="unborder-card"
          @tab-change="handleTabChange"
        >
          <template slot="setting">
            <a
              class="f12"
              :href="GLOBAL.DOC.LOG_QUERY_USER"
              target="_blank"
            > {{ $t('如何查询应用日志') }} </a>
          </template>
          <bk-tab-panel
            v-if="curAppInfo.application.type !== 'cloud_native'"
            name="structured"
            :label="$t('结构化日志')"
          >
            <custom-log
              v-if="tabActive === 'structured'"
              ref="customLog"
            />
          </bk-tab-panel>
          <bk-tab-panel
            name="stream"
            :label="$t('标准输出日志')"
          >
            <standart-log v-if="tabActive === 'stream'" />
          </bk-tab-panel>
          <bk-tab-panel
            name="access"
            :label="$t('访问日志')"
          >
            <access-log
              v-if="tabActive === 'access'"
              ref="accessLog"
            />
          </bk-tab-panel>
        </bk-tab>
      </section>
    </paas-content-loader>
  </div>
</template>

<script>
    import appBaseMixin from '@/mixins/app-base-mixin';
    import appTopBar from '@/components/paas-app-bar';
    import customLog from './custom-log.vue';
    import standartLog from './standart-log.vue';
    import accessLog from './access-log.vue';

    export default {
        components: {
            appTopBar,
            customLog,
            standartLog,
            accessLog
        },
        mixins: [appBaseMixin],
        data () {
            return {
                name: 'log-component',
                tabActive: '',
                tabChangeIndex: 0,
                isLoading: true
            };
        },
        watch: {
            tabActive () {
                this.$nextTick(() => {
                    if (this.tabActive === 'structured') {
                        this.$refs.customLog.initTableBox();
                    }
                    if (this.tabActive === 'access') {
                        this.$refs.accessLog.initTableBox();
                    }
                });
            }
        },
        mounted () {
            this.isLoading = true;
            if (this.$route.query.tab) {
                const isExistTab = ['structured', 'stream', 'access'].includes(this.$route.query.tab);
                this.tabActive = isExistTab ? this.$route.query.tab : 'structured';
            }
            setTimeout(() => {
                this.isLoading = false;
            }, 2000);
        },
        methods: {
            handleTabChange (payload) {
                this.$router.push({
                    name: 'appLog',
                    params: {
                        id: this.$route.params.id,
                        moduleId: this.$route.params.moduleId
                    },
                    query: {
                        tab: payload
                    }
                });
            }
        }
    };
</script>
