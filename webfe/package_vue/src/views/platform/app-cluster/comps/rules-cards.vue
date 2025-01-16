<template>
  <div class="rules-cards">
    <div class="conditional">{{ conditional }}</div>
    <bk-form
      :label-width="200"
      form-type="vertical"
    >
      <bk-form-item
        :label="$t('匹配规则')"
        :required="true"
      >
        <div class="matching-rules">
          <bk-input v-model="formData.name"></bk-input>
          <span class="equal">=</span>
          <bk-input v-model="formData.value"></bk-input>
        </div>
        <p class="select-env">
          <bk-checkbox v-model="isAllocatedByEnv">{{ $t('按环境分配') }}</bk-checkbox>
        </p>
      </bk-form-item>
      <bk-form-item
        v-if="!isAllocatedByEnv"
        :label="$t('集群')"
        :required="true"
        :property="'cluster'"
        :error-display-type="'normal'"
      >
        <ClusterSelect
          @change="clusterSelectChange"
          key="not"
          class="cluster-select-cls"
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
            class="cluster-select-cls"
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
            class="cluster-select-cls"
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
    <div class="tools">
      <div
        class="icon-box plus"
        @click="handleAdd"
      >
        <i class="paasng-icon paasng-plus-thick"></i>
      </div>
      <div class="icon-box down">
        <i class="paasng-icon paasng-back"></i>
      </div>
      <div
        class="icon-box delete"
        @click="handleDelete"
      >
        <i class="paasng-icon paasng-delete"></i>
      </div>
    </div>
  </div>
</template>

<script>
import ClusterSelect from './cluster-select.vue';
export default {
  name: 'RulesCards',
  props: {
    conditional: {
      type: String,
      default: 'if',
    },
  },
  components: {
    ClusterSelect,
  },
  data() {
    return {
      isAllocatedByEnv: false,
      formData: {
        name: '',
        value: '',
      },
      clusters: [],
      envClusters: {},
    };
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
    handleAdd() {
      this.$emit('add');
    },
    handleDelete() {
      this.$emit('delete');
    },
  },
};
</script>

<style lang="scss" scoped>
.rules-cards {
  margin-top: 16px;
  position: relative;
  padding: 24px 16px 8px;
  background: #f5f7fa;
  border-radius: 2px;
  border-top: 3px solid #3a84ff;
  .conditional {
    position: absolute;
    top: -2px;
    left: 0;
    width: 48px;
    height: 21px;
    line-height: 20px;
    font-weight: 700;
    font-size: 12px;
    text-align: center;
    color: #ffffff;
    background: #3a84ff;
    border-radius: 2px 0 8px 0;
  }
  .matching-rules {
    display: flex;
    align-items: center;
    .equal {
      padding: 0 8px;
    }
  }
  .select-env {
    margin-top: 12px;
    line-height: 22px;
  }
  .cluster-select-cls {
    background: #fff;
  }
  .tip {
    margin-top: 4px;
    font-size: 12px;
    color: #979ba5;
    line-height: 20px;
    i {
      transform: translateY(4px);
    }
  }
  .tools {
    position: absolute;
    display: flex;
    flex-direction: column;
    gap: 8px;
    top: 0;
    right: -36px;
    .icon-box {
      display: flex;
      align-items: center;
      justify-content: center;
      width: 28px;
      height: 28px;
      line-height: 28px;
      color: #3a84ff;
      background: #f0f5ff;
      border-radius: 2px;
      cursor: pointer;
      &.plus {
        transform: translateY(1px);
      }
      &.down i {
        transform: rotate(-90deg);
      }
      &.delete {
        color: #ea3636;
        background: #fff0f0;
        i {
          font-size: 16px;
        }
      }
    }
    i {
      font-size: 18px;
    }
  }
}
</style>
