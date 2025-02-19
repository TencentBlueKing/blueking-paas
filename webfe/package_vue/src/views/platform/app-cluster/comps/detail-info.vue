<template>
  <div class="cluster-detail-info">
    <div class="view-title">{{ $t('基本信息') }}</div>
    <DetailsRow
      v-for="(val, key) in baseInfoKeys"
      :key="key"
      :label-width="100"
      :align="key === 'api_servers' ? 'flex-start' : 'center'"
    >
      <template slot="label">{{ `${val}：` }}</template>
      <template slot="value">
        <div
          class="dot-wrapper"
          v-if="key === 'clusterToken'"
        >
          <span
            class="dot"
            v-for="i in 7"
            :key="i"
          ></span>
        </div>
        <template v-else-if="key === 'api_servers'">
          <div v-for="item in data[key]">{{ item }}</div>
        </template>
        <template v-else>{{ data[key] || '--' }}</template>
      </template>
    </DetailsRow>
    <div class="view-title">{{ $t('ElasticSearch 集群信息') }}</div>
    <DetailsRow
      v-for="(val, key) in configKeys"
      :key="key"
      :label-width="100"
    >
      <template slot="label">{{ `${val}：` }}</template>
      <template slot="value">
        <!-- 密码 -->
        <div
          class="dot-wrapper"
          v-if="key === 'password'"
        >
          <template v-if="!data.elastic_search_config?.password">--</template>
          <span
            v-else
            v-for="i in 7"
            class="dot"
            :key="i"
          ></span>
        </div>
        <!-- 协议 -->
        <template v-else-if="key === 'scheme'">
          {{ data.elastic_search_config?.[key]?.join() || '--' }}
        </template>
        <template v-else>{{ data.elastic_search_config?.[key] || '--' }}</template>
      </template>
    </DetailsRow>
    <div class="view-title">{{ $t('可用租户') }}</div>
    <DetailsRow
      v-for="(val, key) in tenantKeys"
      :key="key"
      :label-width="100"
      :align="'flex-start'"
    >
      <template slot="label">{{ `${val}：` }}</template>
      <template slot="value">
        <span
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
export default {
  name: 'DetailInfo',
  components: {
    DetailsRow,
  },
  props: {
    data: {
      type: Object,
      default: () => {},
    },
  },
  data() {
    return {
      baseInfoKeys: {
        name: this.$t('集群名称'),
        description: this.$t('集群描述'),
        cluster_source: this.$t('集群来源'),
        bcs_project_name: this.$t('项目'),
        bcs_cluster_name: this.$t('BCS 集群'),
        bk_biz_name: this.$t('业务'),
        api_servers: this.$t('集群 Server'),
        clusterToken: this.$t('集群 Token'),
        container_log_dir: this.$t('容器日志目录'),
        access_entry_ip: this.$t('集群访问入口 IP'),
      },
      configKeys: {
        scheme: this.$t('协议'),
        host: this.$t('主机'),
        port: this.$t('端口'),
        username: this.$t('用户名'),
        password: this.$t('密码'),
      },
      tenantKeys: {
        available_tenant_ids: this.$t('可用租户'),
      },
    };
  },
};
</script>

<style lang="scss" scoped>
.cluster-detail-info {
  .dot-wrapper {
    display: flex;
    align-items: center;
    gap: 5px;
  }
  .dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: #4d4f56;
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
  &:first-child {
    margin-top: 0;
  }
}
</style>
