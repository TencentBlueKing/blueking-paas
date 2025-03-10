<template>
  <div
    class="component-config-container card-style"
    v-bkloading="{ isLoading: contentLoading, zIndex: 10 }"
  >
    <div class="card-title">{{ $t('安装信息') }}</div>
    <!-- 组件配置 -->
    <bk-form
      :label-width="155"
      :model="formData"
      ref="formRef"
      ext-cls="component-form-cls"
    >
      <bk-form-item
        v-for="item in componentConfigOptions"
        :label="$t(item.label)"
        :required="item.required"
        :property="item.property"
        :rules="item.rules"
        :key="item.label"
        :error-display-type="'normal'"
      >
        <ConfigInput
          v-if="item.type === 'input'"
          v-model="formData[item.property]"
          :type="item.type"
        />
        <bk-radio-group
          v-else-if="item.type === 'radio'"
          v-model="formData[item.property]"
          class="radio-group-cls"
        >
          <bk-radio
            v-for="r in item.radios"
            :value="r.value"
            :key="r.value"
          >
            <span class="ml5 mr5">{{ $t(r.label) }}</span>
            <span class="radio-tip">
              <i class="paasng-icon paasng-info-line"></i>
              {{ $t(r.tip) }}
            </span>
          </bk-radio>
        </bk-radio-group>
        <!-- 应用域名 -->
        <div v-else>
          <DomainsInput
            ref="appDomains"
            :data="formData.app_domains"
          ></DomainsInput>
        </div>
        <p
          v-if="item.tips"
          slot="tip"
          class="item-tips"
        >
          {{ $t(item.tips) }}
        </p>
      </bk-form-item>
    </bk-form>
  </div>
</template>

<script>
import { componentConfigOptions } from './form-options';
import ConfigInput from './comps/config-input.vue';
import DomainsInput from './comps/domains-input.vue';
import { pick } from 'lodash';
export default {
  name: 'ComponentConfig',
  components: {
    ConfigInput,
    DomainsInput,
  },
  props: {
    clusterId: {
      type: String,
      default: '',
    },
  },
  data() {
    return {
      componentConfigOptions,
      contentLoading: false,
      clusterDetails: {},
      formData: {
        // 命名空间
        component_preferred_namespace: 'blueking',
        // 镜像仓库
        component_image_registry: 'hub.bktencent.com',
        // 应用访问类型 subpath、subdomain
        app_address_type: 'subpath',
        // 应用域名(子域名、子路径)
        app_domains: [],
      },
    };
  },
  created() {
    // 获取集群详情
    if (this.clusterId) {
      this.getClusterDetails(this.clusterId);
    }
  },
  methods: {
    // 获取集群详情
    async getClusterDetails(clusterName) {
      this.contentLoading = true;
      try {
        const ret = await this.$store.dispatch('tenant/getClusterDetails', {
          clusterName,
        });
        this.clusterDetails = ret;
        const {
          component_preferred_namespace,
          component_image_registry,
          app_address_type = 'subpath',
          app_domains,
        } = ret;
        this.formData = {
          component_preferred_namespace,
          component_image_registry,
          app_address_type,
          app_domains,
        };
        this.$nextTick(() => {
          this.$refs.appDomains[0]?.setFormData(app_domains);
        });
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.contentLoading = false;
      }
    },
    formValidate() {
      return Promise.all([this.$refs.formRef?.validate(), this.$refs.appDomains[0]?.validate()]);
    },
    getFormData() {
      let data = pick(this.formData, ['component_preferred_namespace', 'component_image_registry', 'app_address_type']);
      data.app_domains = this.$refs.appDomains[0]?.getData();
      return {
        ...this.clusterDetails,
        ...data,
      };
    },
  },
};
</script>

<style lang="scss" scoped>
.component-config-container {
  padding: 16px 24px;
  .component-form-cls {
    width: 635px;
  }
  .item-tips {
    margin-top: 4px;
    font-size: 12px;
    color: #979ba5;
    line-height: 20px;
  }
  .radio-group-cls {
    display: flex;
    flex-direction: column;
    gap: 8px;
    margin-top: 3px;
    /deep/ .bk-form-radio {
      margin-left: 0 !important;
      line-height: 22px;
      white-space: nowrap;
    }
    .radio-tip {
      font-size: 12px;
      color: #979ba5;
    }
  }
}
</style>
