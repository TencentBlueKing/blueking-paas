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
      <bk-collapse
        v-model="activeNames"
        ext-cls="setting-collapse-cls"
      >
        <bk-collapse-item name="1">
          <div class="card-title">
            <i
              class="paasng-icon paasng-right-shape"
              :class="{ expand: isExpanded }"
            ></i>
            <span>{{ $t('高级设置') }}</span>
            <span class="sub-tip ml8">
              {{ $t('可通过为节点设置污点，并在开发者中心配置容忍度，以将应用部署到指定的集群节点上') }}
            </span>
          </div>
          <div
            class="card-content"
            slot="content"
          >
            <bk-form
              :label-width="400"
              form-type="vertical"
              ref="formRef"
              ext-cls="component-form-cls"
            >
              <bk-form-item
                :label="$t('节点选择器（nodeSelector）')"
                :property="'node_selector'"
                ext-cls="node-selector-form-cls"
              >
                <i
                  v-if="!isNodeVisible"
                  v-bk-tooltips="$t('添加')"
                  class="paasng-icon paasng-plus-thick"
                  @click="handleAdd('node_selector')"
                ></i>
                <KeyValueInput
                  v-else
                  ref="keyValueInput"
                  :data="details"
                  :zero="true"
                  @zero="isNodeVisible = false"
                />
              </bk-form-item>
              <bk-form-item
                :label="$t('容忍度（tolerations）')"
                :property="'tolerations'"
                ext-cls="tolerations-form-cls"
              >
                <i
                  v-if="!isTolerationsVisible"
                  v-bk-tooltips="$t('添加')"
                  class="paasng-icon paasng-plus-thick"
                  @click="handleAdd('tolerations')"
                ></i>
                <TolerationsForm
                  v-else
                  ref="tolerationsForm"
                  :data="details"
                  :zero="true"
                  @zero="isTolerationsVisible = false"
                />
              </bk-form-item>
            </bk-form>
          </div>
        </bk-collapse-item>
      </bk-collapse>
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
      activeNames: [],
      isNodeVisible: false,
      isTolerationsVisible: false,
    };
  },
  computed: {
    isExpanded() {
      return this.activeNames.length > 0;
    },
  },
  created() {
    this.getClusterDetails();
  },
  methods: {
    // 高级设置表单校验
    formValidate() {
      if (!this.isExpanded) {
        return Promise.resolve(true);
      }
      const validations = [
        this.isNodeVisible && this.$refs.keyValueInput?.validate(),
        this.isTolerationsVisible && this.$refs.tolerationsForm?.validate(),
      ].filter(Boolean);
      return validations.length ? Promise.all(validations) : Promise.resolve(true);
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
    handleAdd(type) {
      // 容忍度
      if (type === 'tolerations') {
        this.isTolerationsVisible = true;
        return;
      }
      this.isNodeVisible = true;
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
    .card-title {
      margin-bottom: 0;
      i {
        font-size: 12px;
        color: #4d4f56;
        transition: all 0.2s;
        margin-right: 6px;
        transform: translateY(-1px);
        &.expand {
          transform: rotate(90deg);
        }
      }
    }
    .card-content {
      margin-top: 18px;
      padding-left: 68px;
      .paasng-plus-thick {
        font-size: 18px;
        cursor: pointer;
      }
    }
  }
  .component-form-cls {
    .node-selector-form-cls {
      width: 830px;
    }
    .tolerations-form-cls {
      width: 950px;
    }
  }
  .setting-collapse-cls {
    /deep/ .bk-collapse-item .bk-collapse-item-header {
      padding: 0;
      height: auto !important;
      .fr {
        display: none;
      }
    }
  }
}
</style>
