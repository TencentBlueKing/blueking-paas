<template>
  <div class="key-value-form-container">
    <bk-form
      :label-width="0"
      :model="formData"
      ref="validateForm"
      ext-cls="key-value-form-cls"
    >
      <!-- 空数据 -->
      <bk-button
        v-if="!formData.metricCollection.length"
        ext-cls="add-metric-params"
        :text="true"
        title="primary"
        @click="handleCollectionOperation('add')">
        <i class="paasng-icon paasng-plus-thick" />
        {{ $t('新建 Metric 参数') }}
      </bk-button>
      <div
        v-else
        class="row-item"
        v-for="(item, index) in formData.metricCollection"
        :key="index"
      >
        <bk-form-item
          :label="''"
          :property="'metricCollection.' + index + '.key'"
        >
          <bk-input v-model="item.key" @input="handleChange"></bk-input>
        </bk-form-item>
        <span class="equal">=</span>
        <bk-form-item
          :label="''"
          :property="'metricCollection.' + index + '.value'"
        >
          <bk-input v-model="item.value" @input="handleChange"></bk-input>
        </bk-form-item>
        <div class="operation">
          <i class="paasng-icon paasng-plus-circle-shape mr10" @click="handleCollectionOperation('add')"></i>
          <i class="paasng-icon paasng-minus-circle-shape" @click="handleCollectionOperation('sub', index)"></i>
        </div>
      </div>
    </bk-form>
  </div>
</template>

<script>
export default {
  name: 'KeyValueForm',
  props: {
    data: {
      type: [Object, Array],
      default: (() => {}),
    },
  },
  data() {
    return {
      formData: {
        metricCollection: [
          { key: '', value: '' },
        ],
      },
    };
  },
  created() {
    this.init();
  },
  methods: {
    init() {
      // 将接口数据转化
      this.formData.metricCollection = this.formatData(this.data);
    },
    // 数据格式化
    formatData(data) {
      if (Array.isArray(this.data)) {
        return data;
      }
      if (data && !Object.keys(data).length) {
        return [];
      }
      return Object.keys(data).map(key => ({
        key,
        value: data[key],
      }));
    },
    // 校验
    async validateFun() {
      await this.$refs.validateForm?.validate();
    },
    handleCollectionOperation(type, index) {
      if (type === 'add') {
        this.formData.metricCollection.push({
          key: '',
          value: '',
        });
      } else {
        this.formData.metricCollection.splice(index, 1);
      }
    },
    handleChange() {
      this.$emit('update', this.formData.metricCollection);
    },
  },
};
</script>

<style lang="scss" scoped>
.key-value-form-container {
  .add-metric-params {
    line-height: 32px;
  }
  .key-value-form-cls {
    .row-item {
      display: flex;
      align-content: center;
      margin-bottom: 12px;
      &:last-child {
        margin-bottom: 0;
      }
      .bk-form-item {
        flex: 1;
      }
      .equal {
        width: 32px;
        font-weight: 700;
        font-size: 14px;
        color: #ff9c01;
        text-align: center;
      }
      .operation {
        padding: 0 4px 0 9px;
        color: #c4c6cc;
        i {
          cursor: pointer;
        }
      }
    }
  }
}
</style>
