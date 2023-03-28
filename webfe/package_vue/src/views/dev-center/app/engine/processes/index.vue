<template lang="html">
  <div class="right-main">
    <app-top-bar
      :title="$t('进程管理')"
      :can-create="canCreateModule"
      :cur-module="curAppModule"
      :module-list="curAppModuleList"
    />

    <section class="app-container middle">
      <paas-content-loader
        :is-loading="isLoading"
        placeholder="process-loading"
        :offset-top="10"
      >
        <bk-tab
          :key="routeName"
          :active.sync="environment"
          type="unborder-card"
          @tab-change="changeEnv"
        >
          <bk-tab-panel
            name="stag"
            :label="$t('预发布环境')"
          >
            <div class="environment environment-instance">
              <process-operation
                v-if="environment === 'stag'"
                ref="stagComponent"
                :app-code="appCode"
                :environment="'stag'"
                @data-ready="handlerDataReady"
              />
            </div>
          </bk-tab-panel>
          <bk-tab-panel
            name="prod"
            :label="$t('生产环境')"
          >
            <div class="environment environment-instance">
              <process-operation
                v-if="environment === 'prod'"
                ref="prodComponent"
                :app-code="appCode"
                :environment="'prod'"
                @data-ready="handlerDataReady"
              />
            </div>
          </bk-tab-panel>
        </bk-tab>
      </paas-content-loader>

      <div class="process-wrapper">
        <div
          v-if="advisedDocLinks.length"
          class="doc-links-container"
        >
          <h2> {{ $t('帮助文档') }} <span class="tip">- {{ $t('学习如何定义 web 以外的其他应用进程，支持更复杂的应用场景') }}</span></h2>
          <ul class="doc-links-list">
            <li
              v-for="(link, index) in advisedDocLinks"
              :key="index"
            >
              <a
                :href="link.location"
                :title="link.short_description"
                target="_blank"
              >{{ $t(link.title) }}</a>
            </li>
          </ul>
        </div>
      </div>
    </section>
  </div>
</template>

<script>
    import processOperation from './comps/process-operation';
    import appBaseMixin from '@/mixins/app-base-mixin';
    import appTopBar from '@/components/paas-app-bar';

    export default {
        components: {
            processOperation,
            appTopBar
        },
        mixins: [appBaseMixin],
        data () {
            return {
                isLoading: true,
                environment: 'stag',
                advisedDocLinks: []
            };
        },
        computed: {
            routeName () {
                return this.$route.name;
            }
        },
        watch: {
            '$route' (to, from) {
                this.isLoading = true;
            }
        },
        created () {
          this.$store.commit('updataEnvEventData', []);
          this.init();
        },
        beforedestroy () {
          this.$store.commit('updataEnvEventData', ['stag', 'prod']);
        },
        methods: {
            init () {
                this.loadAdvisedDocLinks();
                // 获取当前tab项
                if (this.$route.query && this.$route.query.env === 'prod') {
                    this.environment = 'prod';
                }
            },
            changeEnv (environment) {
                this.isLoading = true;
                if (environment === 'stag') {
                    this.$refs.prodComponent.closeLogDetail();
                } else if (environment === 'prod') {
                    this.$refs.stagComponent.closeLogDetail();
                }
            },
            loadAdvisedDocLinks () {
                const url = `${BACKEND_URL}/api/bkapps/applications/${this.appCode}/accessories/advised_documentary_links/?plat_panel=app_processes&limit=4`;
                this.$http.get(url).then((response) => {
                    this.advisedDocLinks = response.links;
                });
            },
            handlerDataReady (env) {
                setTimeout(() => {
                    this.isLoading = false;
                }, 200);
            }
        }
    };
</script>

<style lang="scss" scoped>
    a {
        cursor: pointer;
    }
    .textarea {
        height: 300px;
    }

    .textarea .inner p {
        height: 25px;
        word-break: break-all;
        white-space: nowrap;
    }

    .environment-instance {
        overflow: visible;
        padding-bottom: 0;
    }

    .doc-links-container {
        margin-top: 5px;

        h2 {
            font-size: 14px;
            color: #55545a;
            font-weight: bold;
            line-height: 22px;
            padding: 5px 0;
            margin-bottom: 6px;

            span.tip {
                font-weight: normal;
                color: #666;
            }
        }

        ul.doc-links-list li {
            border: none;
            padding: 4px 0;
            margin: 0;
            font-size: 14px;
            line-height: 28px;
        }
    }
</style>
