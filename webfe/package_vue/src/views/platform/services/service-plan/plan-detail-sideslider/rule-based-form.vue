<template>
  <div
    class="rule-based-form"
    :key="cardKey"
  >
    <div
      class="rule-card-wrapper"
      v-for="(rule, index) in rulesList"
      :key="index"
    >
      <!-- 左侧卡片区域 -->
      <div class="rule-card">
        <div class="condition-tag">AND</div>
        <!-- 匹配规则 -->
        <bk-form
          :ref="`ruleForm-${index}`"
          form-type="vertical"
          :rules="rules"
          :model="rule"
        >
          <div class="match-rule-row">
            <bk-form-item
              :label="$t('匹配规则')"
              :required="true"
              property="field"
              class="field-form-item"
            >
              <bk-select
                v-model="rule.field"
                class="field-select"
                :placeholder="$t('请选择')"
                :clearable="false"
                @change="handleFieldChange(rule, index)"
              >
                <bk-option
                  v-for="option in fieldOptions"
                  :key="option.value"
                  :id="option.value"
                  :name="option.label"
                ></bk-option>
              </bk-select>
            </bk-form-item>
            <!-- 操作符：固定为等于 -->
            <span class="operator-text">=</span>
            <bk-form-item
              property="value"
              class="value-form-item"
            >
              <!-- 环境字段：使用下拉选择 -->
              <bk-select
                v-if="rule.field === 'environment'"
                v-model="rule.value"
                class="value-input"
                :placeholder="$t('请选择')"
                :clearable="false"
              >
                <bk-option
                  v-for="option in environmentOptions"
                  :key="option.value"
                  :id="option.value"
                  :name="option.label"
                ></bk-option>
              </bk-select>
              <!-- 其他字段：使用标签输入框，支持多值 -->
              <bk-tag-input
                v-else
                v-model="rule.value"
                class="value-input"
                :placeholder="$t('请输入后按 Enter')"
                :allow-create="true"
                :has-delete-icon="true"
                :paste-fn="handlePaste"
              ></bk-tag-input>
            </bk-form-item>
          </div>
        </bk-form>
      </div>
      <div class="action-btns">
        <div
          class="action-btn add-btn"
          v-bk-tooltips="$t('添加规则')"
          @click="handleAdd(index)"
        >
          <i class="paasng-icon paasng-plus-thick"></i>
        </div>
        <!-- 删除按钮（至少保留一条规则） -->
        <div
          v-if="rulesList.length > 1"
          class="action-btn delete-btn"
          v-bk-tooltips="$t('删除')"
          @click="handleDelete(index)"
        >
          <i class="paasng-icon paasng-delete"></i>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { cloneDeep } from 'lodash';

// 默认规则项
const getDefaultRule = () => ({
  field: '',
  operator: 'eq',
  value: [],
});

export default {
  name: 'RuleBasedForm',
  props: {
    // 初始规则数据
    initRules: {
      type: Array,
      default: () => [],
    },
  },
  data() {
    return {
      rulesList: [getDefaultRule()],
      cardKey: 0,
      // 字段选项
      fieldOptions: [
        { value: 'app_id', label: this.$t('应用 ID') },
        { value: 'module_name', label: this.$t('模块名称') },
        { value: 'environment', label: this.$t('环境') },
      ],
      // 环境选项
      environmentOptions: [
        { value: 'stag', label: this.$t('预发布环境') },
        { value: 'prod', label: this.$t('生产环境') },
      ],
      // 表单校验规则
      rules: {
        field: [
          {
            required: true,
            message: this.$t('必填项'),
            trigger: 'blur',
          },
        ],
        value: [
          {
            required: true,
            message: this.$t('必填项'),
            trigger: 'blur',
          },
        ],
      },
    };
  },
  mounted() {
    // 如果有初始数据，则使用初始数据
    if (this.initRules && this.initRules.length > 0) {
      this.rulesList = cloneDeep(this.initRules);
    }
  },
  methods: {
    // 字段变更处理
    handleFieldChange(rule) {
      // 切换字段时重置值（环境为单选字符串，其他为数组）
      rule.value = rule.field === 'environment' ? '' : [];
      this.emitChange();
    },
    // 粘贴处理（支持逗号、空格分隔）
    handlePaste(value) {
      return value.split(/[,，\s]+/).filter(Boolean);
    },
    // 添加规则
    handleAdd(index) {
      this.rulesList.splice(index + 1, 0, getDefaultRule());
      this.cardKey += 1;
      this.emitChange();
    },
    // 删除规则
    handleDelete(index) {
      if (this.rulesList.length > 1) {
        this.rulesList.splice(index, 1);
        this.cardKey += 1;
        this.emitChange();
      }
    },
    // 触发变更事件
    emitChange() {
      this.$emit('change', this.rulesList);
    },
    // 表单校验
    async validate() {
      let isValid = true;
      // 遍历所有规则表单，触发 bk-form 的校验
      for (let i = 0; i < this.rulesList.length; i++) {
        const formRef = this.$refs[`ruleForm-${i}`];
        if (formRef && formRef[0]) {
          try {
            await formRef[0].validate();
          } catch (e) {
            isValid = false;
          }
        }
      }
      return {
        flag: isValid,
        data: this.rulesList,
      };
    },
    // 获取当前数据
    getData() {
      return this.rulesList;
    },
    // 设置数据
    setData(data) {
      if (Array.isArray(data) && data.length > 0) {
        this.rulesList = cloneDeep(data);
        this.cardKey += 1; // 强制刷新视图
      }
    },
  },
};
</script>

<style lang="scss" scoped>
.rule-based-form {
  margin-top: 12px;

  .rule-card-wrapper {
    display: flex;
    align-items: flex-start;
    gap: 8px;
    margin-bottom: 8px;
  }

  .rule-card {
    position: relative;
    flex: 1;
    padding: 24px 16px 16px;
    background: #f5f7fa;
    border-radius: 2px;
    border-top: 3px solid #3a84ff;

    .condition-tag {
      position: absolute;
      top: -2px;
      left: 0;
      min-width: 48px;
      height: 21px;
      padding: 0 8px;
      line-height: 20px;
      font-weight: 700;
      font-size: 12px;
      text-align: center;
      color: #ffffff;
      background: #3a84ff;
      border-radius: 2px 0 8px 0;
    }

    .match-rule-row {
      display: flex;
      align-items: flex-end;
      gap: 8px;

      .field-form-item {
        width: 160px;
        flex-shrink: 0;
        margin-bottom: 0;

        .field-select {
          background: #fff;
        }
      }

      .operator-text {
        width: 32px;
        flex-shrink: 0;
        text-align: center;
        font-size: 14px;
        color: #63656e;
        line-height: 32px;
        margin-bottom: 1px;
      }

      .value-form-item {
        flex: 1;
        margin-bottom: 0;

        .value-input {
          background: #fff;
        }
      }
    }
  }

  .action-btns {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;

    .action-btn {
      display: flex;
      align-items: center;
      justify-content: center;
      width: 28px;
      height: 28px;
      border-radius: 2px;
      cursor: pointer;
      transition: opacity 0.2s;

      i {
        font-size: 18px;
      }

      &:hover {
        opacity: 0.8;
      }
    }

    .add-btn {
      color: #3a84ff;
      background: #f0f5ff;
    }

    .delete-btn {
      color: #ea3636;
      background: rgba(234, 53, 54, 0.1);

      i {
        font-size: 16px;
      }
    }
  }
}
</style>
