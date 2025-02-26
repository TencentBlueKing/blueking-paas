<template>
  <div class="select-cluster-container">
    <!-- 选择集群 -->
    <section class="card-style">
      <div class="card-title">{{ $t('基础信息') }}</div>
      <!-- BCS集群 -->
      <bk-form
        v-if="isBcsCluster"
        :label-width="155"
        :model="infoFormData"
        ref="bcsForm"
        ext-cls="cluster-form-cls"
      >
        <bk-form-item
          v-for="item in bcsOptions"
          :label="$t(item.label)"
          :required="item.required"
          :property="item.property"
          :rules="item.rules"
          :key="item.label"
          :error-display-type="'normal'"
        >
          <ConfigInput
            v-if="['textarea', 'input'].includes(item.type)"
            :type="item.type"
            :maxlength="item.maxlength"
            :disabled="item.disabled"
            v-model="infoFormData[item.property]"
          />
          <ConfigSelect
            v-else-if="item.type === 'select'"
            v-model="infoFormData[item.property]"
            :form-data="infoFormData"
            :property="item.property"
            v-bind="item"
            @change="infoSelectChange"
          />
          <bk-radio-group
            v-else-if="item.type === 'radio'"
            v-model="infoFormData[item.property]"
          >
            <bk-radio
              v-for="r in item.radios"
              :value="r.value"
              :key="r.value"
            >
              <span class="ml5">{{ r.label }}</span>
            </bk-radio>
          </bk-radio-group>
          <p
            v-if="item.tips"
            slot="tip"
            class="item-tips"
          >
            {{ $t(item.tips) }}
            <bk-button
              v-if="item.tipBtn"
              size="small"
              :text="true"
              ext-cls="tip-btn"
            >
              {{ item.tipBtn }}
            </bk-button>
          </p>
        </bk-form-item>
      </bk-form>
      <!-- K8S集群 -->
      <bk-form
        v-else
        :label-width="155"
        :model="infoFormData"
        ref="k8sForm"
        ext-cls="cluster-form-cls"
      >
        <bk-form-item
          v-for="item in displayK8sOptions"
          :label="$t(item.label)"
          :required="item.required"
          :property="item.property"
          :rules="item.rules"
          :key="item.label"
          :error-display-type="'normal'"
        >
          <ConfigInput
            v-if="['textarea', 'input'].includes(item.type)"
            :type="item.type"
            :maxlength="item.maxlength"
            :disabled="item.disabled"
            v-model="infoFormData[item.property]"
          />
          <ConfigSelect
            v-else-if="item.type === 'select'"
            v-model="infoFormData[item.property]"
            :form-data="infoFormData"
            :property="item.property"
            v-bind="item"
            @change="infoSelectChange"
          />
          <div v-else-if="item.type === 'arr-input'">
            <InputList ref="apiServices" />
          </div>
          <bk-radio-group
            v-else-if="item.type === 'radio'"
            v-model="infoFormData[item.property]"
          >
            <bk-radio
              v-for="r in item.radios"
              :value="r.value"
              :key="r.value"
            >
              <span class="ml5">{{ r.label }}</span>
            </bk-radio>
          </bk-radio-group>
          <p
            v-if="item.tips"
            slot="tip"
            class="item-tips"
          >
            {{ $t(item.tips) }}
            <bk-button
              v-if="item.tipBtn"
              size="small"
              :text="true"
              ext-cls="tip-btn"
            >
              {{ item.tipBtn }}
            </bk-button>
          </p>
        </bk-form-item>
      </bk-form>
    </section>
    <section class="card-style">
      <div class="card-title">
        <span>{{ $t('ElasticSearch 集群信息') }}</span>
        <span class="sub-tip ml8">
          {{ $t('用于采集应用日志，配置在下一步安装 bkapp-log-collection 组件时也会使用到') }}
        </span>
      </div>
      <bk-form
        :label-width="155"
        :model="elasticSearchFormData"
        ref="clusterInfoForm"
        ext-cls="cluster-form-cls"
      >
        <bk-form-item
          v-for="item in elasticSearchOptions"
          :label="$t(item.label)"
          :required="item.required"
          :property="item.property"
          :rules="item.rules"
          :key="item.label"
          :error-display-type="'normal'"
        >
          <ConfigInput
            v-if="['password', 'input'].includes(item.type)"
            v-model="elasticSearchFormData[item.property]"
            :type="item.type"
          />
          <ConfigSelect
            v-else-if="item.type === 'select'"
            v-model="elasticSearchFormData[item.property]"
            v-bind="item"
          />
        </bk-form-item>
      </bk-form>
    </section>
    <section class="card-style">
      <div class="card-title">
        <span>{{ $t('可用租户') }}</span>
        <span class="sub-tip ml8">
          {{ $t('哪些租户在集群分配的时候可以看到这个集群') }}
        </span>
      </div>
      <bk-form
        :label-width="155"
        :model="infoFormData"
        ref="tenantForm"
        ext-cls="cluster-form-cls"
      >
        <bk-form-item
          v-for="item in availableTenantsOptions"
          :label="$t(item.label)"
          :required="item.required"
          :property="item.property"
          :rules="item.rules"
          :key="item.label"
          :error-display-type="'normal'"
        >
          <ConfigSelect
            v-model="infoFormData[item.property]"
            v-bind="item"
          />
        </bk-form-item>
      </bk-form>
    </section>
  </div>
</template>

<script>
import {
  bcsOptions,
  k8sOptions,
  tokenOptions,
  certOptions,
  elasticSearchOptions,
  availableTenantsOptions,
} from './form-options';
import ConfigInput from './comps/config-input.vue';
import ConfigSelect from './comps/config-select.vue';
import InputList from './comps/input-list.vue';
import { pick } from 'lodash';

export default {
  name: 'SelectCluster',
  components: {
    ConfigInput,
    ConfigSelect,
    InputList,
  },
  data() {
    return {
      bcsOptions,
      k8sOptions,
      tokenOptions,
      certOptions,
      elasticSearchOptions,
      availableTenantsOptions,
      infoFormData: {
        name: '',
        description: '',
        //集群来源
        cluster_source: 'bcs',
        // 项目
        bcs_project_id: '',
        // Bcs集群id
        bcs_cluster_id: '',
        // 业务
        bk_biz_id: '',
        // 集群 servers （类型为数组，bcs只有一项，k8s可添加多项）
        api_servers: '',
        // 集群 Token
        token: '',
        // 容器日志目录
        container_log_dir: '',
        // 集群访问入口IP
        access_entry_ip: '',
        // 可用租户
        available_tenant_ids: [],
        // k8s集群数据 - 集群认证方式
        auth_type: 'token',
        // APIServers
        api_servers_list: [],
        // 证书认证机构
        ca: '',
        // 客户端证书
        cert: '',
        // 客户端密钥
        key: '',
      },
      // ElasticSearch 集群信息
      elasticSearchFormData: {
        // 协议http/https
        scheme: '',
        // 主机
        host: '',
        port: '',
        username: '',
        password: '',
      },
      curProjectData: {},
      urlTmpl: '',
    };
  },
  computed: {
    isBcsCluster() {
      return this.infoFormData.cluster_source === 'bcs';
    },
    isToken() {
      return this.infoFormData.auth_type === 'token';
    },
    displayK8sOptions() {
      if (this.isToken) {
        return [
          ...k8sOptions.slice(0, 4), // 取出 k8sOptions 的第一个元素之前的部分
          ...tokenOptions,
          ...k8sOptions.slice(4),
        ];
      }
      return [
        ...k8sOptions.slice(0, 4), // 取出 k8sOptions 的第一个元素之前的部分
        ...certOptions,
        ...k8sOptions.slice(4),
      ];
    },
  },
  watch: {
    'infoFormData.cluster_source'(newVal) {
      this.infoFormData.auth_type = 'token';
    },
    'infoFormData.bcs_cluster_id'(newVal) {
      this.infoFormData.api_servers = newVal ? this.urlTmpl.replace('{cluster_id}', newVal) : '';
    },
  },
  created() {
    this.getClusterServerUrlTmpl();
  },
  methods: {
    infoSelectChange(data) {
      // 设置业务值
      if (data.property === 'bcs_project_id') {
        this.curProjectData = data.data;
        this.infoFormData.bk_biz_id = data.data.biz_name;
      }
    },
    // 获取bcs访问地址模版
    async getClusterServerUrlTmpl() {
      try {
        const ret = await this.$store.dispatch('tenant/getClusterServerUrlTmpl');
        this.urlTmpl = ret.url_tmpl;
      } catch (e) {
        this.catchErrorHandler(e);
      }
    },
    formatBcsData() {
      let data = pick(this.infoFormData, [
        'name',
        'description',
        'cluster_source',
        'bcs_project_id',
        'bcs_cluster_id',
        'token',
        'container_log_dir',
        'access_entry_ip',
        'available_tenant_ids',
      ]);
      // 业务
      data.bk_biz_id = this.curProjectData.biz_id;
      data.api_servers = [this.infoFormData.api_servers];
      // ElasticSearch 集群信息
      data.elastic_search_config = { ...this.elasticSearchFormData };
      return data;
    },
    // 格式化k8s集群数据
    formatK8sData() {
      let data = null;
      if (this.isToken) {
        data = pick(this.infoFormData, [
          'name',
          'description',
          'cluster_source',
          'auth_type',
          'token',
          'container_log_dir',
          'access_entry_ip',
          'available_tenant_ids',
        ]);
      } else {
        data = pick(this.infoFormData, [
          'name',
          'description',
          'cluster_source',
          'auth_type',
          'ca',
          'cert',
          'key',
          'container_log_dir',
          'access_entry_ip',
          'available_tenant_ids',
        ]);
      }
      // APIServers
      data.api_servers = this.$refs.apiServices[0]?.getData();
      // ElasticSearch 集群信息
      data.elastic_search_config = { ...this.elasticSearchFormData };
      return data;
    },
    // 表单校验
    formValidate() {
      // APIServers 组件校验
      let validateArr = [this.$refs.clusterInfoForm.validate(), this.$refs.tenantForm.validate()];
      if (this.isBcsCluster) {
        // bcs校验
        validateArr.unshift(this.$refs.bcsForm.validate());
      } else {
        // k8s校验
        validateArr.unshift(...[this.$refs.k8sForm.validate(), this.$refs.apiServices[0]?.validate()]);
      }
      return Promise.all(validateArr);
    },
    getFormData() {
      // BCS集群
      if (this.isBcsCluster) {
        return this.formatBcsData();
      }
      // K8S集群
      return this.formatK8sData();
    },
  },
};
</script>

<style lang="scss" scoped>
.select-cluster-container {
  .card-style {
    padding: 16px 24px;
    margin-bottom: 16px;
    &:last-child {
      margin-bottom: 0;
    }
  }
  .item-tips {
    font-size: 12px;
    color: #979ba5;
    line-height: 20px;
    .tip-btn {
      padding: 0;
    }
  }
  .card-title {
    font-weight: 700;
    font-size: 14px;
    color: #313238;
    line-height: 22px;
    margin-bottom: 18px;
    .sub-tip {
      font-weight: 400;
      font-size: 12px;
      color: #979ba5;
      line-height: 20px;
    }
  }
  .cluster-form-cls {
    width: 635px;
  }
}
</style>
