<template>
  <div class="tolerations-form-container">
    <bk-form
      :label-width="0"
      :model="formData"
      ref="formRef"
      ext-cls="input-list-form-cls"
    >
      <div
        v-for="(item, index) in formData.nodes"
        class="form-item-wrapper"
        :key="index"
      >
        <bk-form-item
          label=""
          :required="true"
          :rules="ruleInput"
          :property="'nodes.' + index + '.key'"
          ext-cls="item-input-cls"
        >
          <bk-input
            v-model="item.key"
            ext-cls="input-cls"
          ></bk-input>
        </bk-form-item>
        <!-- 运算符 -->
        <bk-form-item
          label=""
          :required="true"
          :rules="ruleSelect"
          :property="'nodes.' + index + '.operator'"
        >
          <bk-select
            v-model="item.operator"
            style="width: 160px"
            :placeholder="$t('运算符')"
          >
            <bk-option
              v-for="option in operatorList"
              :key="option.name"
              :id="option.name"
              :name="option.name"
            ></bk-option>
          </bk-select>
        </bk-form-item>
        <bk-form-item
          label=""
          :required="true"
          :rules="ruleInput"
          :property="'nodes.' + index + '.value'"
          ext-cls="item-input-cls"
        >
          <bk-input
            v-model="item.value"
            ext-cls="input-cls"
          ></bk-input>
        </bk-form-item>
        <!-- 不调度 -->
        <bk-form-item
          label=""
          :required="true"
          :rules="ruleSelect"
          :property="'nodes.' + index + '.effect'"
        >
          <bk-select
            v-model="item.effect"
            style="width: 200px"
          >
            <bk-option
              v-for="option in effectList"
              :key="option.id"
              :id="option.id"
              :name="option.name"
            ></bk-option>
          </bk-select>
        </bk-form-item>
        <!-- 时间 -->
        <bk-form-item
          label=""
          :required="true"
          :rules="ruleInput"
          :icon-offset="30"
          :property="'nodes.' + index + '.tolerationSeconds'"
        >
          <bk-input
            style="width: 104px"
            type="number"
            :max="1000"
            :min="0"
            :initial-control-value="0"
            v-model="item.tolerationSeconds"
          >
            <div slot="append">s</div>
          </bk-input>
        </bk-form-item>
        <div class="tools">
          <i
            v-show="nodesLength > 1"
            class="paasng-icon paasng-minus-circle-shape"
            @click="delServer(index)"
          ></i>
          <i
            v-show="nodesLength - 1 === index"
            class="paasng-icon paasng-plus-circle-shape"
            @click="addServer()"
          ></i>
        </div>
      </div>
    </bk-form>
  </div>
</template>

<script>
export default {
  name: 'TolerationsForm',
  props: {
    data: {
      type: Object,
      default: () => {},
    },
  },
  data() {
    return {
      formData: {
        nodes: [{ key: '', operator: '', value: '', effect: '', tolerationSeconds: 0 }],
      },
      // 运算符列表
      operatorList: [{ name: 'Equal' }, { name: 'Exists' }],
      effectList: [
        { id: 'NoSchedule', name: this.$t('不调度（NoSchedule）') },
        { id: 'PreferNoSchedule', name: this.$t('倾向不调度（PreferNoSchedule）') },
        { id: 'NoExecute', name: this.$t('不执行（NoExecute）') },
      ],
      ruleInput: [
        {
          required: true,
          message: this.$t('请输入'),
          trigger: 'blur',
        },
      ],
      ruleSelect: [
        {
          required: true,
          message: this.$t('请选择'),
          trigger: 'blur',
        },
      ],
    };
  },
  computed: {
    nodesLength() {
      return this.formData.nodes.length;
    },
  },
  watch: {
    data: {
      handler(newValue) {
        this.$set(this.formData, 'nodes', newValue.tolerations ?? []);
        if (!this.formData.nodes?.length) {
          this.addServer();
        }
      },
      deep: true,
      immediate: true,
    },
  },
  methods: {
    addServer() {
      this.formData.nodes.push({ key: '', operator: '', value: '', effect: '', tolerationSeconds: 0 });
    },
    delServer(index) {
      this.formData.nodes.splice(index, 1);
    },
    validate() {
      return this.$refs.formRef.validate();
    },
    getData() {
      return this.formData.nodes;
    },
  },
};
</script>

<style lang="scss" scoped>
.tolerations-form-container {
  .item-title {
    display: flex;
    align-items: center;
    color: #4d4f56;
    div {
      flex: 1;
      &:last-child {
        margin-left: -28px;
      }
    }
  }
  .input-list-form-cls {
    display: flex;
    flex-direction: column;
    /deep/ .bk-form-item {
      margin-top: 0 !important;
      .input-cls {
        width: 100%;
      }
    }
    /deep/ .group-append {
      width: 23px;
      text-align: center;
      line-height: 30px;
      font-size: 14px;
      color: #4d4f56;
      flex-shrink: 0;
      background: #fafbfd;
    }
    .tools {
      min-width: 52px;
      flex-shrink: 0;
      display: flex;
      align-items: center;
      gap: 10px;
      margin-left: 2px;
    }
    .paasng-icon {
      cursor: pointer;
      line-height: 32px;
      font-size: 16px;
      color: #979ba5;
    }
  }
  .form-item-wrapper {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 8px;
    /deep/ .item-input-cls {
      flex: 1;
    }
    .sign {
      flex-shrink: 0;
      font-size: 14px;
      color: #4d4f56;
      margin: 0 8px;
      &.sign-hide {
        margin: 0;
        width: 8px;
      }
    }
  }
}
</style>
