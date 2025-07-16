<template>
  <div class="repository-detail-container">
    <DetailsRow
      v-for="(val, key) in displayDetailMap"
      :label-width="110"
      :label="`${$t(val)}：`"
      :class="{ json: jsonProps.includes(key) }"
      :key="key"
    >
      <template slot="value">
        <div
          v-if="jsonProps.includes(key)"
          class="json-pretty"
        >
          <vue-json-pretty
            class="paas-vue-json-pretty-cls"
            :data="data[key]"
            :show-length="true"
            :expanded="Object.keys(data[key] ?? {})?.length"
            :highlight-mouseover-node="true"
          />
        </div>
        <div v-else-if="key === 'is_display'">
          <span :class="['tag', { yes: data[key] }]">
            {{ data[key] ? $t('是') : $t('否') }}
          </span>
        </div>
        <span v-else>{{ data[key] || '--' }}</span>
      </template>
    </DetailsRow>
  </div>
</template>

<script>
import VueJsonPretty from 'vue-json-pretty';
import 'vue-json-pretty/lib/styles.css';
import DetailsRow from '@/components/details-row';

export default {
  name: 'RepositoryDetail',
  components: {
    DetailsRow,
    VueJsonPretty,
  },
  props: {
    data: {
      type: Object,
      default: () => {},
    },
    tabActive: {
      type: String,
      default: 'baseInfo',
    },
  },
  data() {
    return {
      jsonProps: ['preset_services_config', 'required_buildpacks', 'processes'],
      baseInfo: {
        name: '模版名称',
        type: '模版类型',
        render_method: '渲染方式',
        display_name_zh_cn: '展示名称（中）',
        display_name_en: '展示名称（英）',
        description_zh_cn: '描述（中）',
        description_en: '描述（英）',
        language: '开发语言',
        is_display: '是否展示',
      },
      default: {
        blob_url: '二进制包存储路径',
      },
      plugin: {
        repo_type: '代码仓库类型',
        repo_url: '代码仓库地址',
        source_dir: '代码目录',
      },
      config: {
        preset_services_config: '预设增强服务配置',
        required_buildpacks: '必须的构建工具',
        processes: '进程配置',
      },
    };
  },
  computed: {
    displayDetailMap() {
      return this[this.tabActive] || this.baseInfo;
    },
  },
};
</script>

<style lang="scss" scoped>
.repository-detail-container {
  /deep/ .details-row.json .value {
    width: 100%;
  }
  .json-pretty {
    padding: 8px;
    background: #f5f7fa;
    border-radius: 2px;
    .paas-vue-json-pretty-cls {
      /deep/ .vjs-value {
        white-space: pre-wrap !important;
      }
    }
  }
}
</style>
