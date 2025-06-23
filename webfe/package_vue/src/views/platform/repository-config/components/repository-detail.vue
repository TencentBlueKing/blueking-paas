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
        <div v-else-if="key === 'enabled'">
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
      jsonProps: [
        'server_config',
        'oauth_display_info_zh_cn',
        'oauth_display_info_en',
        'display_info_zh_cn',
        'display_info_en',
      ],
      baseInfo: {
        name: '服务名称',
        label_zh_cn: '标签（中文）',
        label_en: '标签（英文）',
        enabled: '是否默认开放',
        spec_cls: '配置类',
        server_config: '服务配置',
      },
      oauth: {
        authorization_base_url: 'OAuth 授权链接',
        client_id: 'Client ID',
        client_secret: 'Client Secret',
        redirect_uri: '回调地址',
        token_base_url: '获取 Token 链接',
        oauth_display_info_zh_cn: 'OAuth 信息（中）',
        oauth_display_info_en: 'OAuth 信息（英）',
      },
      display: {
        display_info_zh_cn: '绑定信息（中）',
        display_info_en: '绑定信息（英）',
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
