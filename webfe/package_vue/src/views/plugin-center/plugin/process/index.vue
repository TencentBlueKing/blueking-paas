<template>
  <div class="app-container middle">
    <paas-content-loader
      :is-loading="isProdLoading"
      placeholder="process-loading"
      :offset-top="10"
    >
      <paas-plugin-title />
      <div class="process-box">
        <process-operation
          ref="prodComponent"
          :app-code="pluginId"
          :environment="'prod'"
          @data-ready="handlerDataReady"
        />
      </div>
    </paas-content-loader>
  </div>
</template>

<script>
    import paasPluginTitle from '@/components/pass-plugin-title';
    import processOperation from '@/views/dev-center/app/engine/processes/comps/process-operation.vue';

    export default {
        components: {
            paasPluginTitle,
            processOperation
        },
        data () {
            return {
                isProdLoading: true
            };
        },
        computed: {
            pdId () {
                return this.$route.params.pluginTypeId;
            },
            pluginId () {
                return this.$route.params.id;
            }
        },
        methods: {
            handlerDataReady (env) {
                setTimeout(() => {
                    if (env === 'prod') {
                        this.isProdLoading = false;
                    }
                }, 200);
            }
        }
    };
</script>

<style lang="scss" scoped>
.plugin-top-title {
    margin-top: 6px;
}
.process-box {
    margin-top: 15px;
}
</style>
