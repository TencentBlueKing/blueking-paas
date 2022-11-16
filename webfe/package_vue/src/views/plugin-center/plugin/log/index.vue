<template lang="html">
  <div
    :key="appCode"
    class="right-main"
  >
    <h2>{{ $t('日志查询') }}</h2>

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
    import standartLog from './standart-log.vue';
    import accessLog from './access-log.vue';

    export default {
        components: {
            standartLog,
            accessLog
        },
        mixins: [appBaseMixin],
        data () {
            return {
                name: 'log-component',
                tabActive: 'stream',
                tabChangeIndex: 0,
                isLoading: false
            };
        },
        watch: {
            tabActive () {
                // this.$nextTick(() => {
                //     if (this.tabActive === 'structured') {
                //         this.$refs.customLog.initTableBox();
                //     }
                //     if (this.tabActive === 'access') {
                //         this.$refs.accessLog.initTableBox();
                //     }
                // });
            }
        },
        mounted () {
            this.isLoading = true;
            if (this.$route.query.tab) {
                const isExistTab = ['stream', 'access'].includes(this.$route.query.tab);
                this.tabActive = isExistTab ? this.$route.query.tab : 'stream';
            }
            setTimeout(() => {
                this.isLoading = false;
            }, 2000);
        },
        methods: {
            handleTabChange (payload) {
                this.$router.push({
                    name: 'pluginLog',
                    params: {
                        id: this.$route.params.id,
                        moduleId: this.$route.params.pluginTypeId
                    },
                    query: {
                        tab: payload
                    }
                });
            }
        }
    };
</script>
