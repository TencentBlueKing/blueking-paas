<template>
  <div class="deploy-network">
    <!-- 服务发现 -->
    <config-item
      :data="serviceFormData"
      data-name="serviceFormData"
      :config="serviceData"
      @refresh="getServiceDiscoveryData"
    />

    <!-- 域名解析规则 -->
    <config-item
      ref="hostAliasesRef"
      :data="domainRuleDFormData"
      data-name="dnsRuleFormData"
      :config="dnsRuleData"
      @save="handleSave"
    />

    <!-- DNS 服务器 -->
    <config-item
      ref="nameserversRef"
      :data="dnsServeFormData"
      data-name="dnsServerData"
      :config="dnsServeData"
      @save="handleSave"
    />
  </div>
</template>

<script>
import appBaseMixin from '@/mixins/app-base-mixin.js';
import configItem from './config-item.vue';
export default {
  components: {
    configItem,
  },
  mixins: [appBaseMixin],
  data() {
    return {
      serviceData: {
        title: this.$t('服务发现'),
        tips: this.$t('通过环境变量或配置文件 获取其他应用的访问地址。'),
        headerCol: [this.$t('应用ID'), this.$t('模块名称')],
        url: true,
        list: [],
      },
      dnsRuleData: {
        title: this.$t('域名解析规则'),
        tips: this.$t('应用可通过 hostAliases 字段来添加额外的域名解析规则（效果等同于向 /etc/hosts 文件中追加条目)'),
        headerCol: ['IP', this.$t('域名')],
        list: [],
      },
      dnsServeData: {
        title: this.$t('DNS 服务器'),
        tips: this.$t('应用可通过 nameservers 字段来设置 DNS 服务器 (效果等同于配置 /etc/resolv.conf 文件)'),
        headerCol: ['nameserver'],
        list: [],
      },
      serviceFormData: [],
      domainRuleDFormData: [],
      dnsServeFormData: [],
    };
  },
  async created() {
    // 服务发现
    this.getServiceDiscoveryData();
    this.getDomainResolutionData();
  },
  methods: {
    // 获取服务发现 （404 为无数据）
    async getServiceDiscoveryData() {
      try {
        const res = await this.$store.dispatch('deploy/getServiceDiscoveryData', { appCode: this.appCode });
        this.serviceData.list = res.bk_saas.map(v => ({ key: v.bk_app_code, value: v.module_name || '--' }));
        // 服务发现表单数据
        this.serviceFormData = res.bk_saas || [];
      } catch (error) {
        // 该接口404为无数据状态
        this.serviceData.list = [];
        this.serviceFormData = [];
      }
    },
    // 获取域名解析和DNS服务器
    async getDomainResolutionData() {
      try {
        const res = await this.$store.dispatch('deploy/getDomainResolutionData', { appCode: this.appCode });
        this.dnsRuleData.list = res.host_aliases.map(v => ({ key: v.ip, value: v.hostnames }));
        // 域名解析规则表单数据
        this.domainRuleDFormData = res.host_aliases || [];
        this.dnsServeData.list = res.nameservers || [];
        // DNS服务器表单数据
        this.dnsServeFormData = res.nameservers || [];
      } catch (error) {
        // 404 无数据, 数据重置
        this.dnsRuleData.list = [];
        this.dnsServeData.list = [];
        this.domainRuleDFormData = [];
        this.dnsServeFormData = [];
      } finally {
        this.$emit('set-network-loading', false);
      }
    },
    handleSave(data) {
      const params = {
        [data.key]: data.value,
      };
      // 当前的数据进行合并
      if (data.key === 'nameservers') {
        params.host_aliases = this.domainRuleDFormData;
      } else {
        params.nameservers = this.dnsServeFormData;
      }
      this.saveDomainResolutionData(params, data.key);
    },
    // 全量保存域名解析、NDS服务器
    async saveDomainResolutionData(data, key) {
      try {
        await this.$store.dispatch('deploy/saveDomainResolutionData', {
          appCode: this.appCode,
          data,
        });
        this.$paasMessage({
          theme: 'success',
          message: this.$t('保存成功'),
        });
        if (key === 'nameservers') {
          this.$refs.nameserversRef.isEdit = false;
        } else {
          this.$refs.hostAliasesRef.isEdit = false;
        }
        // 更新域名解析、NDS服务器
        this.getDomainResolutionData();
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || this.$t('接口异常'),
        });
      }
    },
  },
};
</script>
