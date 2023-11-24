<template>
  <div class="more-info mt20">
    <ul>
      <li
        class="info-item"
        v-for="(item, index) in viewData"
        :key="index"
      >
        <div class="label">{{ item.title }}</div>
        <div
          class="value"
          v-if="Array.isArray(item.default)"
        >
          {{ item.default.length ? item.default?.join(',') : '--' }}
        </div>
        <div
          class="value"
          v-else
        >
          {{ item.default }}
        </div>
      </li>
    </ul>
  </div>
</template>

<script>
export default {
  name: 'MoreInfo',
  data() {
    return {
      schemaFormData: {},
      schema: {},
      viewData: [],
    };
  },
  computed: {
    curPluginInfo() {
      return this.$store.state.plugin.curPluginInfo;
    },
    moreInfoFields() {
      return this.curPluginInfo.extra_fields;
    },
  },
  created() {
    this.fetchPluginTypeList();
  },
  methods: {
    // 获取更多信息表单数据
    async fetchPluginTypeList() {
      try {
        const results = await this.$store.dispatch('plugin/getPluginsTypeList');
        const curPluginType = results.find(v => v.plugin_type?.id === this.curPluginInfo.pd_id);
        // 当前插件类型
        const extraFields = curPluginType.schema?.extra_fields;
        this.viewData = [];
        // 对数据进行填充
        // eslint-disable-next-line no-restricted-syntax
        for (const key in extraFields) {
          if (this.moreInfoFields[key]) {
            extraFields[key].default = this.moreInfoFields[key];
          } else {
            const { type } = extraFields[key];
            if (type === 'array') {
              extraFields[key].default = [];
            }
          }
          // 查看态数据
          this.viewData.push({ title: extraFields[key].title, default: extraFields[key].default });
        }

        this.$emit('set-schema', { type: 'object', properties: extraFields });
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      }
    },
  },
};
</script>

<style lang="scss" scoped>
.more-info {
  .info-item {
    font-size: 12px;
    display: flex;
    .label {
      display: flex;
      justify-content: center;
      align-items: center;
      width: 180px;
      height: 42px;
      border: 1px solid #dcdee5;
      background: #fafbfd;
    }
    .value {
      flex: 1;
      height: 42px;
      border: 1px solid #dcdee5;
      padding-left: 25px;
      padding-right: 10px;
      background: #fff;
      line-height: 42px;
      border-left: none;
    }
    &:not(:last-child) {
      .label,
      .value {
        border-bottom: none;
      }
    }
  }
}
</style>
