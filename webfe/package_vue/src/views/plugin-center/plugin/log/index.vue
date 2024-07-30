<template lang="html">
  <div
    :key="pluginId"
    class="right-main"
  >
    <paas-plugin-title />
    <paas-content-loader
      class="app-container log-middle"
      :is-loading="isLoading"
      placeholder="log-loading"
      :offset-top="60"
      :is-customize-width="true"
    >
      <section class="card-style">
        <bk-tab
          :active.sync="tabActive"
          type="unborder-card"
          @tab-change="handleTabChange"
        >
          <bk-tab-panel
            v-if="pluginFeatureFlags.STRUCTURE_LOG"
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
            v-if="pluginFeatureFlags.STDOUT_LOG"
          >
            <standart-log v-if="tabActive === 'stream'" />
          </bk-tab-panel>
          <bk-tab-panel
            name="access"
            :label="$t('访问日志')"
            v-if="pluginFeatureFlags.ACCESS_LOG"
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
import pluginBaseMixin from '@/mixins/plugin-base-mixin';
import standartLog from './standart-log.vue';
import accessLog from './access-log.vue';
import customLog from './custom-log.vue';
import paasPluginTitle from '@/components/pass-plugin-title';

export default {
  components: {
    standartLog,
    accessLog,
    customLog,
    paasPluginTitle,
  },
  mixins: [pluginBaseMixin],
  data() {
    return {
      name: 'log-component',
      tabActive: 'structured',
      tabChangeIndex: 0,
      isLoading: false,
    };
  },
  computed: {
    pluginFeatureFlags() {
      return this.$store.state.plugin.pluginFeatureFlags;
    },
  },
  mounted() {
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
    handleTabChange(payload) {
      this.$router.push({
        name: 'pluginLog',
        params: {
          id: this.$route.params.id,
          moduleId: this.$route.params.pluginTypeId,
        },
        query: {
          tab: payload,
        },
      });
    },
  },
};
</script>

