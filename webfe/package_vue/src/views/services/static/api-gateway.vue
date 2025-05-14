<template lang="html">
  <service-general :data="apiData" />
</template>

<script>
import serviceGeneral from '@/components/serviceGeneral';
export default {
  components: {
    serviceGeneral,
  },
  data() {
    return {
      apiData: {
        name: this.$t('API 网关'),
        hasLink: true,
        link: this.GLOBAL.LINK.APIGW_INDEX,
        apititle: this.$t('API 网关'),
        image: '/static/images/API Gateway.png',
        apiexplain: this.$t(
          '蓝鲸API网关服务，帮助开发者创建、发布、维护、监控和保护 API，以快速、低成本、低风险地对外开放蓝鲸应用或其他系统的数据或服务'
        ),
        apiList: [
          {
            title: this.$t('API资源管理'),
            explain: this.$t('网关负责人可以对API 资源进行创建、开放、关闭等操作，并且支持YAML、JSON格式批量导入。'),
          },
          {
            title: this.$t('网关认证'),
            explain: this.$t('集成鉴权体系，支持对蓝鲸应用和用户进行身份认证，获取蓝鲸应用和用户身份信息。'),
          },
          {
            title: this.$t('流量控制'),
            explain: this.$t('支持在网关或 API 资源层面进行流量控制。'),
          },
          {
            title: this.$t('安全防护'),
            explain: this.$t('支持 SSL 加密，并支持采用 JWT 向后端接口传递应用/用户信息。'),
          },
          {
            title: this.$t('监控告警'),
            explain: this.$t(
              '提供可视化的 API 实时监控，包括：请求数、失败请求数、平均响应时间、统计响应时间，以便实时掌握 API 运行情况。'
            ),
          },
        ],
      },
    };
  },
};
</script>
