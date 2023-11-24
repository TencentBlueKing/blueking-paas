<template>
  <div class="more-info-edit">
    <div class="app-container middle">
      <paas-plugin-title />
      <BkSchemaForm
        class="mt20 bk-form-warp"
        v-model="schemaFormData"
        ref="bkForm"
        :http-adapter="{ request }"
        :label-width="170"
        :schema="schema"
      ></BkSchemaForm>
      <section class="action-button-group">
        <bk-button
          theme="primary"
          class="mr10"
          @click="handlerSave"
        >
          {{ $t('保存') }}
        </bk-button>
        <bk-button
          theme="default"
          @click="goBack"
        >
          {{ $t('取消') }}
        </bk-button>
      </section>
    </div>
  </div>
</template>

<script>
import http from '@/api';
import createForm from '@blueking/bkui-form';
import paasPluginTitle from '@/components/pass-plugin-title';
import pluginBaseMixin from '@/mixins/plugin-base-mixin';

const BkSchemaForm = createForm();
export default {
  name: 'MoreInfoEdit',
  components: {
    BkSchemaForm,
    paasPluginTitle,
  },
  mixins: [pluginBaseMixin],
  data() {
    return {
      schemaFormData: {},
      schema: {},
      isLoading: true,
    };
  },
  computed: {
    curPluginInfo() {
      return this.$store.state.plugin.curPluginInfo;
    },
  },
  created() {
    this.schema = this.$route.params.schema;
    if (!this.schema) {
      const schema = localStorage.getItem('pluginSchema');
      this.schema = JSON.parse(schema);
    }
  },
  methods: {
    async request(url) {
      url = `${window.BACKEND_URL}/api/bk_plugin_distributors/`;
      try {
        const data = await http.get(url);
        return data.map(e => ({ label: e.name, value: e.code_name }));
      } catch (error) {
        console.warn(error);
      }
    },
    // 保存基本信息
    async updatePluginBaseInfo() {
      const data = {
        extra_fields: this.schemaFormData,
      };
      try {
        await this.$store.dispatch('plugin/updatePluginMoreInfo', {
          pdId: this.pdId,
          pluginId: this.pluginId,
          data,
        });
        this.$bkMessage({
          theme: 'success',
          message: this.$t('基本信息修改成功！'),
        });
        this.$router.push({
          name: 'pluginBaseInfo',
          params: {
            id: this.curPluginInfo.id,
          },
        });
        // 获取创建基本信息
        await this.$store.dispatch('plugin/getPluginInfo', { pluginId: this.pluginId, pluginTypeId: this.pdId });
      } catch (e) {
        this.$bkMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      }
    },
    handlerSave() {
      this.updatePluginBaseInfo();
    },
    goBack() {
      this.$router.go(-1);
    },
  },
};
</script>

<style lang="scss" scoped>
.more-info-edit {
  .action-button-group{
    margin-left: 170px;
    margin-top: 20px;
  }
}
</style>
