<template>
  <bk-form
    :label-width="0"
    form-type="inline"
    :ref="`prodRefKey${index}`"
    class="pord-from-cls"
    :model="row"
    :rules="rules"
  >
    <bk-form-item
      :required="true"
      :property="prop"
    >
      <bk-select
        v-if="type === 'select'"
        v-model="row[prop]"
        :clearable="false"
        class="pord-input-cls"
        ext-cls="select-custom-cls">
        <bk-option
          v-for="option in list"
          :key="option.name"
          :id="option.name"
          :name="option.name"
          v-bk-tooltips="{ content: $t('访问入口不支持 UDP'), disabled: !(row.exposed_type?.name && option.name === 'UDP') }"
          :disabled="row.exposed_type?.name && option.name === 'UDP'">
        </bk-option>
      </bk-select>
      <bk-input
        v-else
        v-model="row[prop]"
        class="pord-input-cls"
      />
    </bk-form-item>
  </bk-form>
</template>

<script>
export default {
  props: {
    row: Object,
    index: Number,
    prop: String,
    rules: Object,
    list: Array,
    type: {
      type: String,
      default: 'input',
    },
  },
  methods: {
    validate() {
      return this.$refs[`prodRefKey${this.index}`].validate();
    },
  },
};
</script>

<style lang="scss" scoped>
.pord-from-cls {
  width: 100%;
  /deep/ .bk-form-item {
    width: 100%;
    .bk-form-content {
      width: 100%;
      .tooltips-icon {
        right: 5px !important;
      }
    }
  }
  .select-custom-cls {
    background: #fff;
  }
}
</style>
