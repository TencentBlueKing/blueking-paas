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
          <template v-if="!!queryClusterId && specialPropertys.includes(item.property)">
            <!-- 更新集群信息，特定字段为禁用状态、编辑态-有 xx_name 优先展示 xx_name -->
            <ConfigInput
              type="input"
              :disabled="true"
              :value="infoFormData[item.editProperty] || infoFormData[item.property]"
            />
          </template>
          <template v-else>
            <!-- 项目-禁用编辑显示 -->
            <ConfigInput
              v-if="!!queryClusterId && item.property === 'bk_biz_id'"
              type="input"
              :disabled="true"
              :value="infoFormData[item.editProperty] || infoFormData[item.property]"
            />
            <ConfigInput
              v-else-if="['textarea', 'input', 'password'].includes(item.type)"
              :type="item.type"
              :maxlength="item.maxlength"
              :disabled="item.disabled || (!!queryClusterId && editDisabledPropertys.includes(item.property))"
              v-model="infoFormData[item.property]"
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
                :class="{ 'border-tip': !!r.tip }"
                v-bk-tooltips="{ content: $t(r.tip), disabled: !r.tip, width: 385 }"
              >
                <span class="ml5">{{ $t(r.label) }}</span>
              </bk-radio>
            </bk-radio-group>
            <!-- bcs - 集群 Server 特殊处理 -->
            <div v-else-if="Array.isArray(item.type)">
              <!-- BCS 网关 -->
              <ConfigInput
                v-if="infoFormData.api_address_type === 'bcs_gateway'"
                type="input"
                :disabled="true"
                v-model="infoFormData[item.property]"
              />
              <!-- 自定义 -->
              <InputList
                ref="clusterServices"
                v-else
              />
            </div>
          </template>
          <p
            v-if="item.tips"
            slot="tip"
            class="item-tips"
            v-bk-overflow-tips
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
            :disabled="item.disabled || (!!queryClusterId && editDisabledPropertys.includes(item.property))"
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
            style="width: 680px"
          >
            <!-- disabledFn 内部判断是否禁用 -->
            <bk-radio
              v-for="r in item.radios"
              :value="r.value"
              :key="r.value"
              :class="{ 'border-tip': !!r.tip }"
              v-bk-tooltips="{ content: $t(r.tip), disabled: !r.tip, width: 385 }"
              :disabled="r.disabledFn && r.disabledFn(infoFormData.cluster_source)"
            >
              <span class="ml5">{{ $t(r.label) }}</span>
            </bk-radio>
          </bk-radio-group>
          <p
            v-if="item.tips"
            slot="tip"
            class="item-tips"
            v-bk-overflow-tips
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
    <!-- 非必填折叠 -->
    <section class="card-style setting">
      <bk-collapse
        v-model="activeNames"
        ext-cls="setting-collapse-cls"
      >
        <bk-collapse-item name="elastic">
          <div class="card-title">
            <i
              class="paasng-icon paasng-right-shape"
              :class="{ expand: isExpanded }"
            ></i>
            <span>{{ $t('ElasticSearch 集群信息') }}</span>
            <span class="sub-tip ml8">
              {{ $t('用于采集应用日志，该配置将在后续安装 bkapp-log-collection 时会生效') }}
            </span>
          </div>
          <div
            style="margin-top: 18px"
            slot="content"
          >
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
                />
                <ConfigSelect
                  v-else-if="item.type === 'select'"
                  v-model="elasticSearchFormData[item.property]"
                  v-bind="item"
                />
              </bk-form-item>
            </bk-form>
          </div>
        </bk-collapse-item>
      </bk-collapse>
    </section>
    <section class="card-style">
      <div class="card-title">
        <span>{{ $t('镜像仓库') }}</span>
        <span class="sub-tip ml8">
          {{ $t('应用构建时生成的镜像会推送到这里') }}
        </span>
      </div>
      <bk-form
        :label-width="155"
        :model="mirrorRepositoryFormData"
        ref="imageRepositoryRef"
        ext-cls="cluster-form-cls"
      >
        <!-- image_repository 有值的时候才会展示  -->
        <bk-form-item
          v-if="defaultImageRepository"
          :label="$t('使用独立镜像仓库')"
          :error-display-type="'normal'"
        >
          <bk-switcher
            v-model="isImageRepository"
            theme="primary"
          ></bk-switcher>
          <p
            slot="tip"
            class="item-tips"
            v-bk-overflow-tips
          >
            {{ `${$t('不启用时，使用平台公共的镜像仓库')}：${defaultImageRepository}` }}
          </p>
        </bk-form-item>
        <template v-if="isImageRepository">
          <bk-form-item
            v-for="item in displayMirrorRepositoryOptions"
            :label="$t(item.label)"
            :required="item.required"
            :property="item.property"
            :rules="item.rules"
            :key="item.label"
            :error-display-type="'normal'"
          >
            <ConfigInput
              v-if="['password', 'input'].includes(item.type)"
              v-model="mirrorRepositoryFormData[item.property]"
              :type="item.type"
              :placeholder="$t(item.placeholder)"
            />
            <bk-switcher
              v-else
              v-model="mirrorRepositoryFormData[item.property]"
              theme="primary"
            ></bk-switcher>
            <p
              v-if="item.tips"
              slot="tip"
              class="item-tips"
              v-bk-overflow-tips
            >
              {{ $t(item.tips) }}
            </p>
          </bk-form-item>
        </template>
      </bk-form>
    </section>
    <section class="card-style">
      <div class="card-title">
        <span>{{ $t('租户信息') }}</span>
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
  mirrorRepositoryOptions,
} from '../form-options';
import ConfigInput from '../comps/config-input.vue';
import ConfigSelect from '../comps/config-select.vue';
import InputList from '../comps/input-list.vue';
import { pick } from 'lodash';
import { mapState } from 'vuex';

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
        // 集群 API 地址类型
        api_address_type: 'bcs_gateway',
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
      // 编辑态特殊处理
      specialPropertys: ['bcs_cluster_id', 'bcs_project_id'],
      editDisabledPropertys: ['name'],
      activeNames: [],
      // 镜像仓库数据
      mirrorRepositoryFormData: {
        host: '',
        namespace: '',
        username: '',
        password: '',
        skip_tls_verify: false,
      },
      // 使用独立镜像仓库
      isImageRepository: true,
      clusterDefaultConfigs: {},
    };
  },
  computed: {
    ...mapState({
      curUserInfo: (state) => state.curUserInfo,
      platformFeature: (state) => state.platformFeature,
    }),
    displayBcsOptions() {
      return this.queryClusterId ? this.updateRequiredFields(bcsOptions, ['token']) : bcsOptions;
    },
    displayElasticSearchOptions() {
      const options = this.queryClusterId
        ? this.updateRequiredFields(elasticSearchOptions, ['password'])
        : elasticSearchOptions;
      if (this.platformFeature.BK_LOG) {
        // BK_LOG 为 ture，form 为非必填
        return options.map((item) => {
          return {
            ...item,
            required: false,
            rules: [],
          };
        });
      }
      return options;
    },
    displayK8sOptions() {
      return this.queryClusterId
        ? this.updateRequiredFields(this.correspondingK8sOptions, ['token', 'ca', 'cert', 'key'])
        : this.correspondingK8sOptions;
    },
    isBcsCluster() {
      return this.infoFormData.cluster_source === 'bcs';
    },
    isToken() {
      return this.infoFormData.auth_type === 'token';
    },
    // 组合对应的formitem
    correspondingK8sOptions() {
      return [
        ...k8sOptions.slice(0, 4), // 提取前四个元素
        ...(this.isToken ? tokenOptions : certOptions),
        ...k8sOptions.slice(4),
      ];
    },
    isEdit() {
      return this.$route.path.endsWith('/edit');
    },
    // 存在id说明集群已经创建
    queryClusterId() {
      return this.$route.query?.id || '';
    },
    customAPIAddress() {
      return this.infoFormData.api_address_type === 'custom';
    },
    // 默认平台镜像仓库
    defaultImageRepository() {
      return this.clusterDefaultConfigs?.image_repository;
    },
    // 镜像仓库form配置
    displayMirrorRepositoryOptions() {
      return mirrorRepositoryOptions;
    },
    isExpanded() {
      return this.activeNames.length > 0;
    },
  },
  watch: {
    // 集群 API 地址类型
    'infoFormData.cluster_source'(newVal) {
      // k8s 只允许自定义
      if (newVal === 'native_k8s') {
        this.infoFormData.api_address_type = 'custom';
      }
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
      this.getClusterDefaultConfigs();
    }
    this.getClusterServerUrlTmpl();
  },
  methods: {
    // 去掉指定属性的必填属性
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
      };
      // ElasticSearch 集群信息
      this.elasticSearchFormData = {
        ...this.elasticSearchFormData,
        ...(data.elastic_search_config || {}),
      };
      // k8s APIServers 数据（数组）
      this.$set(this.infoFormData, 'api_servers_list', data.api_servers);
      // apiServices 数据回填
      const apiServers = data.api_servers.map((v) => {
        return { value: v };
      });
      // 回填 Servers
      this.$nextTick(() => {
        this.$refs.apiServices[0]?.setData(apiServers);
        if (this.infoFormData.api_address_type === 'custom') {
          this.$refs.clusterServices[0]?.setData(apiServers);
        }
        // bcs apiserver
        if (this.infoFormData.api_address_type === 'bcs_gateway') {
          this.infoFormData.api_servers = data.api_servers.length ? data.api_servers.join() : '';
        }
      });
      // 镜像仓库数据回填
      if (data.app_image_registry !== null && Object.keys(data.app_image_registry)?.length) {
        this.mirrorRepositoryFormData = { ...data.app_image_registry };
      }
      this.getClusterDefaultConfigs();
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
    // 获取集群默认配置项
    async getClusterDefaultConfigs() {
      try {
        const ret = await this.$store.dispatch('tenant/getClusterDefaultConfigs');
        this.clusterDefaultConfigs = ret;
        if (this.isEdit) {
          // 编辑状态，app_image_registry 有值直接显示镜像仓库表单
          this.isImageRepository = this.clusterData.app_image_registry !== null || !this.defaultImageRepository;
        } else {
          this.isImageRepository = !ret.image_repository;
        }
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        // 必填展开 ElasticSearch 集群信息
        this.activeNames = this.platformFeature.BK_LOG ? [] : ['elastic'];
      }
    },
    // 检查每个字段是否为 ''
    areAllFieldsEmptyString(obj) {
      return Object.values(obj).every((value) => value === '');
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
        'api_address_type',
      ]);
      // 业务
      if (this.queryClusterId) {
        // 更新模式
        data.bk_biz_id = this.clusterData.bk_biz_id;
      } else {
        // 新建
        data.bk_biz_id = this.curProjectData.biz_id;
      }
      if (data.api_address_type === 'custom') {
        data.api_servers = this.$refs.clusterServices[0]?.getData();
      } else {
        data.api_servers = [this.infoFormData.api_servers];
      }
      // ElasticSearch 集群信息（非必填、并且无填写时传递null）
      const isEmpty = this.areAllFieldsEmptyString(this.elasticSearchFormData);
      data.elastic_search_config = this.platformFeature.BK_LOG && isEmpty ? null : { ...this.elasticSearchFormData };
      data.app_image_registry = this.isImageRepository ? { ...this.mirrorRepositoryFormData } : null;
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
          'api_address_type',
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
          'api_address_type',
        ]);
      }
      // APIServers
      data.api_servers = this.$refs.apiServices[0]?.getData();
      // ElasticSearch 集群信息
      const isEmpty = this.areAllFieldsEmptyString(this.elasticSearchFormData);
      data.elastic_search_config = this.platformFeature.BK_LOG && isEmpty ? null : { ...this.elasticSearchFormData };
      data.app_image_registry = this.isImageRepository ? { ...this.mirrorRepositoryFormData } : null;
      return data;
    },
    // 表单校验
    formValidate() {
      // APIServers 组件校验
      let validateArr = [this.$refs.clusterInfoForm.validate(), this.$refs.tenantForm.validate()];
      if (this.isImageRepository) {
        validateArr.push(this.$refs.imageRepositoryRef.validate());
      }
      if (this.isBcsCluster) {
        // bcs校验
        validateArr.unshift(this.$refs.bcsForm.validate());
        if (this.customAPIAddress) {
          validateArr.unshift(this.$refs.clusterServices[0]?.validate());
        }
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
    /deep/ .bk-form-radio.border-tip .bk-radio-text span {
      border-bottom: 1px dashed;
    }
    &.setting {
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
            transform: rotate(90deg) translateX(-1px);
          }
        }
      }
    }
  }
  .setting-collapse-cls {
    /deep/ .bk-collapse-item {
      .bk-collapse-item-header {
        padding: 0;
        height: auto !important;
        .fr {
          display: none;
        }
      }
      .bk-collapse-item-content {
        padding: 0 !important;
      }
    }
  }
  .item-tips {
    max-width: 750px;
    width: max-content;
    font-size: 12px;
    color: #979ba5;
    line-height: 20px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    .tip-btn {
      padding: 0;
    }
  }
  .cluster-form-cls {
    width: 635px;
  }
}
</style>
