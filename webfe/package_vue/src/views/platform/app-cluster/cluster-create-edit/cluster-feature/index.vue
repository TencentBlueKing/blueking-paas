<template>
  <div class="cluster-feature-container">
    <!-- 集群特性 -->
    <Feature
      :loading="isLoading"
      :data="details"
      ref="featureRef"
    />
    <!-- 高级设置 -->
    <section
      class="card-style setting"
      v-bkloading="{ isLoading, zIndex: 10 }"
    >
      <div class="card-title">
        <span>{{ $t('高级设置') }}</span>
        <span class="sub-tip ml8">
          {{ $t('可通过为节点设置污点，并在开发者中心配置容忍度，以将应用部署到指定的集群节点上') }}
        </span>
      </div>
      <div class="card-content">
        <bk-form
          :label-width="400"
          form-type="vertical"
          ref="formRef"
          ext-cls="component-form-cls"
        >
          <bk-form-item
            :label="$t('节点选择器（nodeSelector）')"
            :property="'node_selector'"
          >
            <KeyValueInput
              ref="keyValueInput"
              class="nodes-select"
              :data="details"
            />
          </bk-form-item>
          <bk-form-item
            :label="$t('容忍度（tolerations）')"
            :property="'tolerations'"
          >
            <TolerationsForm
              ref="tolerationsForm"
              :data="details"
            />
          </bk-form-item>
        </bk-form>
      </div>
    </section>
  </div>
</template>

<script>
import Feature from './feature.vue';
import KeyValueInput from '../comps/key-value-input.vue';
import TolerationsForm from './tolerations-form.vue';
import { cloneDeep } from 'lodash';
export default {
  name: 'ClusterFeature',
  props: {
    clusterId: {
      type: String,
      default: '',
    },
  },
  components: {
    Feature,
    KeyValueInput,
    TolerationsForm,
  },
  data() {
    return {
      isLoading: false,
      details: {},
    };
  },
  created() {
    this.getClusterDetails();
  },
  methods: {
    formValidate() {
      return Promise.all([this.$refs.keyValueInput?.validate(), this.$refs.tolerationsForm?.validate()]);
    },
    // 获取集群详情
    async getClusterDetails() {
      this.isLoading = true;
      try {
        const ret = await this.$store.dispatch('tenant/getClusterDetails', {
          clusterName: this.clusterId,
        });
        this.details = ret;
        this.$nextTick(() => {
          const transformedArray = Object.entries(ret.node_selector).map(([key, value]) => {
            return {
              key: key,
              value: value,
            };
          });
          this.$refs.keyValueInput?.setData(transformedArray);
        });
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.isLoading = false;
      }
    },
    // 获取高级设置的表单数据
    getSettingsgData() {
      return {
        node_selector: this.$refs.keyValueInput?.getData() ?? {},
        tolerations: this.$refs.tolerationsForm?.getData() ?? [],
      };
    },
    // 表单数据
    getFormData() {
      const feature = this.$refs.featureRef?.getData();
      const settingsData = this.getSettingsgData();
      const data = {
        ...this.details,
        feature_flags: cloneDeep(feature),
        ...settingsData,
      };
      return data;
    },
  },
};
</script>

<style lang="scss" scoped>
.cluster-feature-container {
  .card-style {
    padding: 16px 24px;
  }
  .setting {
    margin-top: 16px;
    .card-content {
      padding-left: 68px;
      padding-right: 120px;
      .nodes-select {
        width: calc(100% - 120px);
      }
    }
  }
}
</style>
