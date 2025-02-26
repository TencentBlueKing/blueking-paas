<template>
  <div class="config-select-container">
    <bk-select
      v-bind="$attrs"
      :value="$attrs.value"
      :loading="selectLoading"
      @change="handleChange"
      ext-cls="config-select-cls"
    >
      <bk-option
        v-for="option in list"
        :key="option.id"
        :id="option.id"
        :name="option.name"
      ></bk-option>
      <template
        v-for="(value, name) in $slots"
        #[name]
      >
        <slot :name="name"></slot>
      </template>
    </bk-select>
  </div>
</template>

<script>
export default {
  name: 'ConfigSelectContainer',
  props: {
    formData: {
      default: () => {},
    },
    source: {
      default: () => {},
    },
    property: {
      type: String,
    },
  },
  data() {
    return {
      list: [],
      selectLoading: false,
    };
  },
  mounted() {
    this.init();
  },
  methods: {
    async init() {
      if (this.source?.api && !this.source.dependency) {
        // 直接获取下拉框列表
        this.getSelectList();
      }
      // 更新集群下拉列表
      if (this.source.dependency) {
        this.$watch(
          () => this.formData[this.source.dependency],
          (newVal) => {
            this.list = [];
            this.$emit('input', '');
            this.getSelectList(newVal);
          }
        );
      }
    },
    // 请求下拉框数据
    async getSelectList(parmas) {
      this.selectLoading = true;
      try {
        this.list = await this.source.api(parmas);
      } catch (e) {
        this.list = [];
        this.catchErrorHandler(e);
      } finally {
        this.selectLoading = false;
      }
    },
    handleChange(data) {
      // 发出更新事件，更新父组件的 v-model
      this.$emit('input', data);
      this.$emit('change', {
        property: this.property,
        data: this.list.find((v) => v.id === data),
      });
    },
  },
};
</script>

<style lang="scss" scoped>
.config-select-container {
  background: #fff;
  &[multiple] {
    .config-select-cls {
      height: auto;
    }
  }
}
</style>
