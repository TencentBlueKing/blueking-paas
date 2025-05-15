<template>
  <div class="cluster-detail-info">
    <bk-button
      class="clustertab-edit-btn-cls"
      theme="primary"
      :outline="true"
      @click="handleEdit"
    >
      {{ $t('编辑') }}
    </bk-button>
    <div class="view-title">{{ $t('基本信息') }}</div>
    <DetailsRow
      v-for="(val, key) in baseInfoKeys"
      :key="key"
      :label-width="labelWidth"
      :align="key === 'api_servers' ? 'flex-start' : 'center'"
    >
      <template slot="label">{{ `${val}：` }}</template>
      <template slot="value">
        <div v-if="key === 'token'">
          <SensitiveText :text="displayInfoData[key]" />
        </div>
        <div
          v-else-if="clusterSource === 'native_k8s' && ['ca', 'cert', 'key'].includes(key)"
          class="certificate"
        >
          <span
            class="text"
            v-bk-tooltips.top="{
              content: displayInfoData[key],
              placement: 'top',
              extCls: 'certificate-tips-cls',
            }"
          >
            {{ displayInfoData[key] || '--' }}
          </span>
          <i
            v-if="displayInfoData[key]"
            class="paasng-icon paasng-general-copy"
            v-copy="displayInfoData[key]"
            v-bk-tooltips="$t('复制')"
          ></i>
        </div>
        <template v-else-if="key === 'api_servers'">
          <template v-if="!displayInfoData[key]">--</template>
          <div
            v-else
            v-for="item in displayInfoData[key]"
            :key="item"
          >
            {{ item }}
          </div>
        </template>
        <template v-else>
          {{ key === 'cluster_source' ? clusterSourceMap[displayInfoData[key]] : displayInfoData[key] || '--' }}
        </template>
      </template>
    </DetailsRow>
    <div class="view-title">{{ $t('ElasticSearch 集群信息') }}</div>
    <DetailsRow
      v-for="(val, key) in configKeys"
      :key="key"
      :label-width="labelWidth"
    >
      <template slot="label">{{ `${val}：` }}</template>
      <template slot="value">
        <!-- 密码 -->
        <div v-if="key === 'password'">
          <SensitiveText :text="data.elastic_search_config?.[key]" />
        </div>
        <template v-else>{{ data.elastic_search_config?.[key] || '--' }}</template>
      </template>
    </DetailsRow>
    <div class="view-title">{{ $t('镜像仓库') }}</div>
    <template v-if="data.app_image_registry !== null">
      <DetailsRow
        v-for="(val, key) in imageRegistryKeys"
        :key="val + key"
        :label-width="labelWidth"
      >
        <template slot="label">{{ `${val}：` }}</template>
        <template slot="value">
          <div v-if="key === 'password'">
            <SensitiveText :text="data.app_image_registry?.[key]" />
          </div>
          <template v-else>{{ data.app_image_registry?.[key] || '--' }}</template>
        </template>
      </DetailsRow>
    </template>
    <p
      class="tips"
      v-else
    >
      {{ `${$t('使用平台公共的镜像仓库')}：` }}{{ defaultConfig?.image_repository || '--' }}
    </p>
    <div class="view-title">{{ $t('租户信息') }}</div>
    <DetailsRow
      v-for="(val, key) in tenantKeys"
      :key="key"
      :label-width="labelWidth"
      :align="'flex-start'"
      :label="`${val}：`"
    >
      <template slot="value">
        <span v-if="!data[key]?.length">--</span>
        <span
          v-else
          class="border-tag"
          v-for="id in data[key]"
          :key="id"
        >
          {{ id }}
        </span>
      </template>
    </DetailsRow>
  </div>
</template>

<script>
import DetailsRow from '@/components/details-row';
import SensitiveText from '@/components/sensitive-text';
export default {
  name: 'DetailInfo',
  components: {
    DetailsRow,
    SensitiveText,
  },
  props: {
    data: {
      type: Object,
      default: () => {},
    },
    defaultConfig: {
      type: Object,
      default: () => {},
    },
  },
  data() {
    return {
      configKeys: {
        scheme: this.$t('协议'),
        host: this.$t('主机'),
        port: this.$t('端口'),
        username: this.$t('用户名'),
        password: this.$t('密码'),
      },
      imageRegistryKeys: {
        host: this.$t('镜像仓库域名'),
        namespace: this.$t('命名空间'),
        username: this.$t('用户名'),
        password: this.$t('密码'),
      },
      tenantKeys: {
        available_tenant_ids: this.$t('可用租户'),
      },
      clusterSourceMap: {
        bcs: this.$t('BCS 集群'),
        native_k8s: this.$t('K8S 集群（不推荐，无法使用访问控制台等功能）'),
      },
    };
  },
  computed: {
    localLanguage() {
      return this.$store.state.localLanguage;
    },
    labelWidth() {
      return this.localLanguage === 'en' ? 150 : 100;
    },
    displayInfoData() {
      return {
        ...this.data,
        bcs_project_name: this.data.bcs_project_name || this.data.bcs_project_id,
        bcs_cluster_name: this.data.bcs_cluster_name || this.data.bcs_cluster_id,
        bk_biz_name: this.data.bk_biz_name || this.data.bk_biz_id,
      };
    },
    clusterSource() {
      return this.displayInfoData['cluster_source'];
    },
    baseInfoKeys() {
      const keysArray = [
        { key: 'name', value: this.$t('集群名称') },
        { key: 'description', value: this.$t('集群描述') },
        { key: 'cluster_source', value: this.$t('集群来源') },
        { key: 'bcs_project_name', value: this.$t('项目') },
        { key: 'bcs_cluster_name', value: `BCS ${this.$t('集群')}` },
        { key: 'bk_biz_name', value: this.$t('业务') },
        { key: 'api_servers', value: `${this.$t('集群')} Server` },
        { key: 'token', value: `${this.$t('集群')} Token` },
        { key: 'container_log_dir', value: this.$t('容器日志目录') },
        { key: 'access_entry_ip', value: this.$t('集群访问入口 IP') },
      ];
      // 当 clusterSource 为 'native_k8s' 时，添加证书信息，确保顺序
      if (this.clusterSource === 'native_k8s') {
        keysArray.splice(
          7,
          0, // 插入到正确的位置以保持顺序
          { key: 'ca', value: this.$t('证书认证机构') },
          { key: 'cert', value: this.$t('客户端证书') },
          { key: 'key', value: this.$t('客户端密钥') }
        );
      }
      return keysArray.reduce((acc, item) => {
        acc[item.key] = item.value;
        return acc;
      }, {});
    },
  },
  methods: {
    handleEdit() {
      this.$router.push({
        name: 'clusterCreateEdit',
        params: {
          type: 'edit',
        },
        query: {
          id: this.data.name,
          step: 1,
          alone: true,
        },
      });
    },
  },
};
</script>
<style lang="scss">
.certificate-tips-cls {
  .tippy-content {
    max-width: 620px !important;
  }
}
</style>
<style lang="scss" scoped>
.cluster-detail-info {
  position: relative;
  .tips {
    margin-top: 8px;
    font-size: 12px;
    color: #979ba5;
  }
  .certificate {
    max-width: 480px;
    display: flex;
    align-items: center;
    .text {
      min-width: 0;
      flex: 1;
      white-space: nowrap;
      text-overflow: ellipsis;
      overflow: hidden;
    }
    i {
      flex-shrink: 0;
      font-size: 14px;
      cursor: pointer;
      &:hover {
        color: #3a84ff;
      }
    }
  }
  .border-tag {
    margin-right: 4px;
  }
}
.view-title {
  font-weight: 700;
  font-size: 14px;
  color: #313238;
  line-height: 22px;
  margin-top: 24px;
  &:first-of-type {
    margin-top: 0;
  }
}
</style>
