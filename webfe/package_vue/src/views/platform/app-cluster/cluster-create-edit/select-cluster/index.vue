<template>
  <div
    class="select-cluster-container"
    v-bkloading="{ isLoading: loading, zIndex: 10 }"
  >
    <!-- 选择集群 -->
    <section class="card-style">
      <div class="card-title">{{ $t('基础信息') }}</div>
      <!-- BCS集群 -->
      <bk-form
        v-show="isBcsCluster"
        :label-width="155"
        :model="infoFormData"
        ref="bcsForm"
        ext-cls="cluster-form-cls"
      >
        <bk-form-item
          v-for="item in displayBcsOptions"
          :label="$t(item.label)"
          :required="item.required"
          :property="item.property"
          :rules="item.rules"
          :key="item.label"
          :error-display-type="'normal'"
        >
          <template v-if="queryClusterId && disabledProperty.includes(item.property)">
            <!-- 更新集群信息模型下，特定字段为禁用状态 -->
            <ConfigInput
              type="input"
              :disabled="true"
              v-model="infoFormData[item.property]"
            />
          </template>
          <template v-else>
            <ConfigInput
              v-if="['textarea', 'input', 'password'].includes(item.type)"
              :type="item.type"
              :maxlength="item.maxlength"
              :disabled="item.disabled"
              v-model="infoFormData[item.property]"
              @blur="inputBlur($event, item.property, 'infoFormData')"
              @focus="inputFocus($event, item.property, 'infoFormData')"
            />
            <ConfigSelect
              v-else-if="item.type === 'select'"
              v-model="infoFormData[item.property]"
              :form-data="infoFormData"
              :property="item.property"
              :api-data="clusterData"
              v-bind="item"
              @change="infoSelectChange"
            />
            <bk-radio-group
              v-else-if="item.type === 'radio'"
              v-model="infoFormData[item.property]"
              style="width: 680px"
            >
              <bk-radio
                v-for="r in item.radios"
                :value="r.value"
                :key="r.value"
              >
                <span class="ml5">{{ $t(r.label) }}</span>
              </bk-radio>
            </bk-radio-group>
          </template>
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
        v-show="!isBcsCluster"
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
            v-if="['textarea', 'input', 'password'].includes(item.type)"
            :type="item.type"
            :maxlength="item.maxlength"
            :disabled="item.disabled"
            v-model="infoFormData[item.property]"
            @blur="inputBlur($event, item.property, 'infoFormData')"
            @focus="inputFocus($event, item.property, 'infoFormData')"
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
            style="width: 680px"
          >
            <bk-radio
              v-for="r in item.radios"
              :value="r.value"
              :key="r.value"
            >
              <span class="ml5">{{ $t(r.label) }}</span>
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
          {{ $t('用于采集应用日志，该配置将在后续安装 bkapp-log-collection 时会生效') }}
        </span>
      </div>
      <bk-form
        :label-width="155"
        :model="elasticSearchFormData"
        ref="clusterInfoForm"
        ext-cls="cluster-form-cls"
      >
        <bk-form-item
          v-for="item in displayElasticSearchOptions"
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
            @blur="inputBlur($event, item.property, 'elasticSearchFormData')"
            @focus="inputFocus($event, item.property, 'elasticSearchFormData')"
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
} from '../form-options';
import ConfigInput from '../comps/config-input.vue';
import ConfigSelect from '../comps/config-select.vue';
import InputList from '../comps/input-list.vue';
import { pick } from 'lodash';
import { mapState } from 'vuex';

// token/password默认占位
const featurePlaceholder = '￥%&*~@';

export default {
  name: 'SelectCluster',
  components: {
    ConfigInput,
    ConfigSelect,
    InputList,
  },
  props: {
    clusterData: {
      type: Object,
      default: () => {},
    },
    loading: {
      type: Boolean,
      default: false,
    },
  },
  data() {
    return {
      k8sOptions,
      tokenOptions,
      certOptions,
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
      disabledProperty: ['bcs_cluster_id', 'bcs_project_id'],
    };
  },
  computed: {
    displayBcsOptions() {
      return this.isEdit ? this.updateRequiredFields(bcsOptions, ['token']) : bcsOptions;
    },
    displayElasticSearchOptions() {
      return this.isEdit ? this.updateRequiredFields(elasticSearchOptions, ['password']) : elasticSearchOptions;
    },
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
    isEdit() {
      return this.$route.path.endsWith('/edit');
    },
    ...mapState({
      curUserInfo: (state) => state.curUserInfo,
    }),
    // 存在id说明集群已经创建
    queryClusterId() {
      return this.$route.query?.id || '';
    },
  },
  watch: {
    'infoFormData.cluster_source'(newVal) {
      this.infoFormData.auth_type = 'token';
    },
    // 集群 Server 依赖 bcs_cluster_id
    'infoFormData.bcs_cluster_id'(newVal) {
      this.infoFormData.api_servers = newVal ? this.urlTmpl.replace('{cluster_id}', newVal) : '';
    },
    clusterData: {
      handler(newVal) {
        this.fillFormData(newVal);
      },
      deep: true,
    },
  },
  created() {
    if (this.queryClusterId) {
      this.$emit('get-detail');
    }
    if (!this.isEdit) {
      // 新建回填当前用户租户
      const { tenantId } = this.curUserInfo;
      tenantId && this.infoFormData.available_tenant_ids.push(tenantId);
      this.infoFormData.container_log_dir = '/var/lib/docker/containers';
    }
    this.getClusterServerUrlTmpl();
  },
  methods: {
    updateRequiredFields(options, propertiesToUpdate) {
      return options.map((item) => {
        if (propertiesToUpdate.includes(item.property)) {
          return {
            ...item,
            required: false,
            rules: [],
          };
        }
        return item;
      });
    },
    // 编辑表单数据回填
    fillFormData(data = {}) {
      // bcs、k8s基础信息
      this.infoFormData = {
        ...this.infoFormData,
        ...data,
        bk_biz_id: data.bk_biz_id || '', // 业务
        // bcs apiserver
        api_servers: data.api_servers.length ? data.api_servers.join() : '',
      };
      // ElasticSearch 集群信息
      this.elasticSearchFormData = {
        ...this.elasticSearchFormData,
        ...data.elastic_search_config,
      };
      // 编辑态 token与password不会返回，默认回填六位占位符
      this.$set(this.infoFormData, 'token', featurePlaceholder);
      this.$set(this.elasticSearchFormData, 'password', featurePlaceholder);
      // k8s APIServers 数据（数组）
      this.$set(this.infoFormData, 'api_servers_list', data.api_servers);
      // apiServices 数据回填
      const apiServers = data.api_servers.map((v) => {
        return { value: v };
      });
      this.$refs.apiServices[0]?.setData(apiServers);
    },
    infoSelectChange(data) {
      // 设置业务值
      if (data.property === 'bcs_project_id') {
        this.curProjectData = data?.data || {};
        this.infoFormData.bk_biz_id = data.data?.biz_name || '';
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
        'auth_type',
        'bcs_project_id',
        'bcs_cluster_id',
        'token',
        'container_log_dir',
        'access_entry_ip',
        'available_tenant_ids',
      ]);
      // 业务
      if (this.queryClusterId) {
        // 更新模式
        data.bk_biz_id = this.clusterData.bk_biz_id;
      } else {
        // 新建
        data.bk_biz_id = this.curProjectData.biz_id;
      }
      data.api_servers = [this.infoFormData.api_servers];
      // 清空默认占位符
      data.token = data.token === featurePlaceholder ? '' : data.token;
      // ElasticSearch 集群信息
      const { password } = this.elasticSearchFormData;
      data.elastic_search_config = {
        ...this.elasticSearchFormData,
        password: password === featurePlaceholder ? '' : password,
      };
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
        // 清空默认占位符
        data.token = data.token === featurePlaceholder ? '' : data.token;
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
      const { password } = this.elasticSearchFormData;
      data.elastic_search_config = {
        ...this.elasticSearchFormData,
        password: password === featurePlaceholder ? '' : password,
      };
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
    inputFocus(val, property, dataName) {
      if (this.queryClusterId) {
        if (['token', 'password'].includes(property) && val === featurePlaceholder) {
          this.$set(this[dataName], property, '');
        }
      }
    },
    inputBlur(val, property, dataName) {
      if (this.queryClusterId) {
        if (['token', 'password'].includes(property) && val === '') {
          this.$set(this[dataName], property, featurePlaceholder);
        }
      }
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
  .cluster-form-cls {
    width: 635px;
  }
}
</style>
