<template>
  <div class="uniform-form">
    <bk-form
      :label-width="200"
      form-type="vertical"
      ref="uniformForm"
      :rules="rules"
    >
      <bk-form-item
        v-if="!hasEnv"
        :label="$t('集群')"
        :required="true"
        :property="'cluster'"
        :error-display-type="'normal'"
      >
        <ClusterSelect
          key="not"
          :edit-data="allocationPolicy?.clusters"
          @change="clusterSelectChange"
        />
      </bk-form-item>
      <!-- 统一分配-按环境 -->
      <template v-else>
        <bk-form-item
          :label="$t('集群')"
          :required="true"
          :property="'stagCluster'"
        >
          <ClusterSelect
            key="stag"
            :has-label="true"
            :label="$t('预发布环境')"
            :env="'stag'"
            :edit-data="allocationPolicy?.env_clusters?.stag"
            @change="envClusterSelectChange"
          />
        </bk-form-item>
        <bk-form-item
          :required="true"
          :property="'prodCluster'"
        >
          <ClusterSelect
            key="prod"
            :has-label="true"
            :label="$t('生产环境')"
            :env="'prod'"
            :edit-data="allocationPolicy?.env_clusters?.prod"
            @change="envClusterSelectChange"
          />
        </bk-form-item>
      </template>
    </bk-form>
    <div class="tip flex-row">
      <i class="bk-icon icon-info mr5"></i>
      <div>
        <p>如果配置了多个集群：</p>
        <p>开发者在创建应用时，需要选择集群；如开发者没选择任何值，则使用默认集群。</p>
      </div>
    </div>
  </div>
</template>

<script>
import ClusterSelect from './cluster-select.vue';
import ClusterTransfer from './cluster-transfer.vue';
export default {
  name: 'UniformForm',
  props: {
    hasEnv: {
      type: Boolean,
      default: false,
    },
    isEdit: {
      type: Boolean,
      default: false,
    },
    data: {
      type: Object,
      default: () => ({}),
    },
  },
  components: {
    ClusterSelect,
    ClusterTransfer,
  },
  data() {
    return {
      // 统一分配-不按环境配置
      clusters: [],
      envClusters: {},
      rules: {
        cluster: [
          {
            validator: () => {
              return this.clusters.length;
            },
            message: this.$t('必填项'),
            trigger: 'blur',
          },
        ],
        stagCluster: [
          {
            validator: () => {
              return this.envClusters?.stag?.length;
            },
            message: this.$t('必填项'),
            trigger: 'blur',
          },
        ],
        prodCluster: [
          {
            validator: () => {
              return this.envClusters?.prod?.length;
            },
            message: this.$t('必填项'),
            trigger: 'blur',
          },
        ],
      },
    };
  },
  computed: {
    curTenantData() {
      return this.$store.state.tenant.curTenantData;
    },
    allocationPolicy() {
      if (!this.curTenantData.policies) {
        return {};
      }
      return this.curTenantData.policies.allocation_policy || {};
    },
  },
  methods: {
    // 不按环境
    clusterSelectChange(data) {
      this.clusters = data;
    },
    // 按环境
    envClusterSelectChange(data) {
      this.envClusters = {
        ...this.envClusters,
        ...data,
      };
    },
    // 不按环境
    validate() {
      return new Promise((resolve, reject) => {
        this.$refs.uniformForm?.validate().then(
          () => {
            resolve({
              clusters: this.clusters,
              env_clusters: this.envClusters,
            });
          },
          (e) => {
            console.error(e.content || e);
            reject(e);
          }
        );
      });
    },
  },
};
</script>

<style lang="scss" scoped>
.uniform-form {
  .tip {
    margin-top: 4px;
    font-size: 12px;
    color: #979ba5;
    line-height: 20px;
    i {
      transform: translateY(4px);
    }
  }
}
</style>
