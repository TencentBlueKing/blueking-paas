<template>
  <div>
    <paas-plugin-title />
    <paas-content-loader
      :is-loading="isProdLoading"
      class="app-container"
      placeholder="plugin-process-loading"
      :offset-top="10"
    >
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
import pluginBaseMixin from '@/mixins/plugin-base-mixin';
import processOperation from '@/views/dev-center/app/engine/processes/comps/process-operation.vue';

export default {
  components: {
    paasPluginTitle,
    processOperation,
  },
  mixins: [pluginBaseMixin],
  data() {
    return {
      isProdLoading: true,
    };
  },
  methods: {
    handlerDataReady(env) {
      setTimeout(() => {
        if (env === 'prod') {
          this.isProdLoading = false;
        }
      }, 200);
    },
  },
};
</script>
