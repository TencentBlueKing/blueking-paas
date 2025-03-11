<template>
  <div class="rules-cards">
    <div class="conditional">{{ getConditionalType(allLength, order) }}</div>
    <bk-form
      form-type="vertical"
      ref="rulesCard"
      :rules="rules"
    >
      <div>
        <div
          class="matching-rules-box"
          v-if="!isLastCard"
        >
          <!-- 匹配规则 -->
          <bk-form-item
            :required="true"
            :property="'matcherKey'"
            :icon-offset="31"
          >
            <div class="matching-rules">
              <bk-select
                :disabled="false"
                v-model="data.matcher.key"
                ext-cls="rules-select-custom"
                @change="handleChange"
              >
                <bk-option
                  v-for="option in types"
                  :key="option.key"
                  :id="option.key"
                  :name="option.name"
                ></bk-option>
              </bk-select>
              <span class="equal">=</span>
            </div>
          </bk-form-item>
          <bk-form-item
            :required="true"
            :property="'matcherValue'"
            ext-cls="rules-vlaue"
          >
            <bk-input
              v-model="data.matcher.value"
              :placeholder="placeholder"
            ></bk-input>
          </bk-form-item>
        </div>
        <p
          class="select-env"
          slot="tip"
        >
          <bk-checkbox v-model="data.hasEnv">{{ $t('按环境分配') }}</bk-checkbox>
        </p>
      </div>
      <bk-form-item
        v-if="!data.hasEnv"
        :label="$t('集群')"
        :required="true"
        :property="'cluster'"
        :error-display-type="'normal'"
      >
        <ClusterSelect
          @change="clusterSelectChange"
          key="not"
          :edit-data="data?.clusters"
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
            :edit-data="data?.envClusters?.stag"
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
            :edit-data="data?.envClusters?.prod"
            @change="envClusterSelectChange"
          />
        </bk-form-item>
      </template>
    </bk-form>
    <div class="tip flex-row">
      <i class="bk-icon icon-info mr5"></i>
      <p>{{ $t('如果配置多个集群，开发者在创建应用时需要选择一个，未选择时，使用默认（第一个）集群。') }}</p>
    </div>
    <div
      v-if="!isLastCard"
      class="tools"
    >
      <div
        class="icon-box plus"
        v-bk-tooltips="$t('添加规则')"
        @click="handleAdd"
      >
        <i class="paasng-icon paasng-plus-thick"></i>
      </div>
      <template v-if="allLength > 2">
        <!-- 上移 -->
        <div
          v-if="order === 0"
          class="icon-box down"
          @click="handleMove('down')"
        >
          <i class="paasng-icon paasng-back"></i>
        </div>
        <!-- 下移 -->
        <div
          v-else
          class="icon-box up"
          @click="handleMove('up')"
        >
          <i class="paasng-icon paasng-back"></i>
        </div>
        <div
          class="icon-box delete"
          @click="handleDelete"
        >
          <i class="paasng-icon paasng-delete"></i>
        </div>
      </template>
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
    data: {
      type: Object,
      default: () => ({}),
    },
    allLength: {
      type: Number,
      default: 0,
    },
    order: {
      type: Number,
      default: 0,
    },
    types: {
      type: Array,
      default: () => [],
    },
  },
  components: {
    ClusterSelect,
  },
  data() {
    return {
      isAllocatedByEnv: false,
      formData: {
        key: '',
        value: '',
      },
      envClusters: {},
      rules: {
        matcherKey: [
          {
            validator: () => {
              return this.data.matcher?.key !== '';
            },
            message: this.$t('必填项'),
            trigger: 'blur',
          },
        ],
        matcherValue: [
          {
            validator: () => {
              return this.data.matcher?.value !== '';
            },
            message: this.$t('必填项'),
            trigger: 'blur',
          },
        ],
        cluster: [
          {
            validator: () => {
              return this.data.clusters.length;
            },
            message: this.$t('必填项'),
            trigger: 'blur',
          },
        ],
        stagCluster: [
          {
            validator: () => {
              return this.data.envClusters?.stag?.length;
            },
            message: this.$t('必填项'),
            trigger: 'blur',
          },
        ],
        prodCluster: [
          {
            validator: () => {
              return this.data.envClusters?.prod?.length;
            },
            message: this.$t('必填项'),
            trigger: 'blur',
          },
        ],
      },
    };
  },
  computed: {
    isLastCard() {
      return this.allLength - 1 === this.order;
    },
    curCardMatcher() {
      return this.types.find((v) => v.key === this.data.matcher?.key) ?? {};
    },
    placeholder() {
      const { name = '' } = this.curCardMatcher;
      const lowerCaseName = name.toLocaleLowerCase();
      const endsWithIn = lowerCaseName.endsWith('_in') || lowerCaseName.endsWith('.in');
      return this.$t(endsWithIn ? '请输入，多个值以英文逗号连接' : '请输入');
    },
  },
  methods: {
    // 获取当前规则语句分支
    getConditionalType(arrayLength, currentIndex) {
      if (currentIndex === 0) {
        return 'if';
      } else if (currentIndex === arrayLength - 1) {
        return 'else';
      } else {
        return 'else if';
      }
    },
    // 不按环境
    clusterSelectChange(data) {
      this.data.clusters = data;
    },
    // 按环境
    envClusterSelectChange(data) {
      this.data.envClusters = {
        ...this.data.envClusters,
        ...data,
      };
    },
    handleAdd() {
      this.$emit('add', this.order);
    },
    handleDelete() {
      this.$emit('delete', this.order);
    },
    handleMove(key) {
      this.$emit('move', this.order, key);
    },
    validate() {
      return this.$refs.rulesCard?.validate();
    },
    handleChange() {
      this.data.matcher.value = '';
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
  .matching-rules-box {
    display: flex;
    align-items: flex-end;
    .rules-vlaue {
      flex: 1;
    }
  }
  .matching-rules {
    display: flex;
    align-items: center;
    .rules-select-custom {
      flex-shrink: 0;
      width: 160px;
      background: #fff;
    }
    .equal {
      padding: 0 8px;
    }
  }
  .select-env {
    margin-top: 12px;
    margin-bottom: 6px;
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
      &.up i {
        transform: rotate(90deg);
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
