<template lang="html">
    <div class="right-main">
        <app-top-bar
            :title="$t('网站访问统计')"
            :can-create="canCreateModule"
            :cur-module="curAppModule"
            :module-list="curAppModuleList"
            v-if="isEngineEnabled">
        </app-top-bar>
        <div class="ps-top-bar" v-else>
            <h2> {{ $t('网站访问统计') }} </h2>
        </div>

        <paas-content-loader :is-loading="isLoading" placeholder="analysis-loading" :offset-top="20" class="app-container middle">
            <app-analysis :backend-type="'user_tracker'" tab-name="webAnalysis" :engine-enabled="isEngineEnabled" @data-ready="handleDataReady"></app-analysis>
        </paas-content-loader>
    </div>
</template>

<script>
    import appBaseMixin from '@/mixins/app-base-mixin';
    import appTopBar from '@/components/paas-app-bar';
    import analysis from './comps/analysis';

    export default {
        components: {
            appTopBar: appTopBar,
            appAnalysis: analysis
        },
        mixins: [appBaseMixin],
        data () {
            return {
                isEngineEnabled: true,
                isLoading: true
            };
        },
        watch: {
            '$route' () {
                this.isEngineEnabled = this.curAppInfo.web_config.engine_enabled;
                this.isLoading = true;
            }
        },
        created () {
            this.isEngineEnabled = this.curAppInfo.web_config.engine_enabled;
        },
        methods: {
            handleDataReady () {
                this.isLoading = false;
            }
        }
    };
</script>
