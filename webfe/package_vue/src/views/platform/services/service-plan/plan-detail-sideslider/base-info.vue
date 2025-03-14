<template>
  <div class="plan-base-info-container">
    <bk-button
      class="edit-btns"
      theme="primary"
      :outline="true"
    >
      {{ $t('编辑') }}
    </bk-button>
    <!-- 查看模式 -->
    <DetailsRow
      v-for="(val, key) in baseInfoMap"
      :key="val"
      :label-width="80"
      :label="`${val}：`"
    >
      <div
        v-if="key === 'config'"
        slot="value"
        class="json-pretty"
      >
        <vue-json-pretty
          :data="data[key]"
          :show-length="true"
          :expanded="Object.keys(data[key])?.length"
          :highlight-mouseover-node="true"
        />
      </div>
      <div
        v-else-if="key === 'is_active'"
        slot="value"
      >
        <span :class="['tag', { yes: data[key] }]">{{ data[key] ? $t('是') : $t('否') }}</span>
      </div>
      <div
        v-else
        slot="value"
      >
        {{ data[key] }}
      </div>
    </DetailsRow>
  </div>
</template>

<script>
import DetailsRow from '@/components/details-row';
import VueJsonPretty from 'vue-json-pretty';
import 'vue-json-pretty/lib/styles.css';
export default {
  props: {
    data: {
      type: Object,
      default: () => ({}),
    },
  },
  components: {
    DetailsRow,
    VueJsonPretty,
  },
  data() {
    return {
      baseInfoMap: {
        name: this.$t('方案名称'),
        service_name: this.$t('所属服务'),
        description: this.$t('方案简介'),
        is_active: this.$t('是否可见'),
        config: this.$t('方案配置'),
      },
    };
  },
};
</script>

<style lang="scss" scoped>
.plan-base-info-container {
  position: relative;
  .json-pretty {
    padding: 8px;
    background: #f5f7fa;
    border-radius: 2px;
  }
  .edit-btns {
    position: absolute;
    right: 0;
    top: 8px;
  }
}
</style>
