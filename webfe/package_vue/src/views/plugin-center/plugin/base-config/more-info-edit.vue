<template>
  <div class="more-info-edit">
    <paas-plugin-title />
    <div class="app-container middle">
      <BkSchemaForm
        class="bk-form-warp"
        v-model="schemaFormData"
        ref="bkForm"
        :http-adapter="{ request }"
        :label-width="170"
        :schema="schema"
        :layout="layout"
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
      layout: {
        prop: 0,
        container: {
          display: 'grid',
          gridGap: '0',
        },
      },
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
    this.schema.properties = this.addValidation(this.schema.properties);
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
      this.$refs.bkForm?.validate().then(() => {
        this.updatePluginBaseInfo();
      }, (validator) => {
        console.warn(validator);
      });
    },
    goBack() {
      this.$router.go(-1);
    },
    // 多选添加校验
    addValidation(properties) {
      if (!Object.keys(properties).length) {
        return properties;
      }
      for (const key in properties) {
        if (Object.prototype.hasOwnProperty.call(properties[key], 'ui:rules') && Array.isArray(properties[key].default)) {
          // 多选校验
          properties[key]['ui:rules'] = [
            {
              validator: '{{ $self.value.length > 0 }}',
              message: '必填项',
            },
          ];
        }
      }
      return properties;
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
.bk-form-warp /deep/ .bk-schema-form-item--error {
  [error] {
    border-color: #f5222d !important;
  }
  .bk-schema-form-item__error-tips{
    color: #f5222d;
  }
}
.bk-form-warp /deep/ .bk-form-item .bk-form-content .bk-select {
  background-color: #fff;
}
</style>
