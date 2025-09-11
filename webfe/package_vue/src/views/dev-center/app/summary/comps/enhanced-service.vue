<template>
  <CardItem>
    <template #title>
      <div class="flex-row align-items-baseline">
        <span class="card-title mr-8">{{ $t('增强服务') }}</span>
        <bk-button
          text
          title="primary"
          class="p0 f12"
          @click="jumpToServices"
        >
          {{ $t('查看详情') }}
        </bk-button>
      </div>
    </template>
    <template #title-extra>
      <span class="title-extra">
        <bk-select
          v-model="activeModule"
          style="width: 116px"
          :clearable="false"
          :disabled="!curAppModuleList?.length"
          behavior="simplicity"
          searchable
          @change="getEnhancedService"
        >
          <bk-option
            v-for="option in curAppModuleList"
            :key="option.name"
            :id="option.name"
            :name="option.name"
          />
        </bk-select>
      </span>
    </template>
    <div
      class="service-items-container mt-12"
      v-bkloading="{ isLoading: isLoading, zIndex: 10 }"
    >
      <!-- 已启用 -->
      <template v-if="enabledServices.length">
        <div class="f12 mb-12">{{ $t('已启用') }}</div>
        <div class="service-items">
          <ServiceItem
            v-for="item in enabledServices"
            :data="item"
            :key="item.uuid"
            @click.native="jumpToServices(item, 'detail')"
          />
        </div>
      </template>
      <!-- 未启用 -->
      <template v-if="unenabledServices.length">
        <div class="f12 mb-12 mt-12">{{ $t('未启用') }}</div>
        <div class="service-items">
          <ServiceItem
            v-for="item in unenabledServices"
            :data="item"
            :is-enabled="false"
            :key="item.uuid"
          />
        </div>
      </template>
    </div>
  </CardItem>
</template>

<script>
import CardItem from './card-item.vue';
import ServiceItem from './service-item.vue';
import appBaseMixin from '@/mixins/app-base-mixin';

export default {
  name: 'EnhancedService',
  mixins: [appBaseMixin],
  components: {
    CardItem,
    ServiceItem,
  },
  data() {
    return {
      activeModule: '',
      isLoading: false,
      enabledServices: [],
      unenabledServices: [],
    };
  },
  watch: {
    curAppModuleList: {
      handler() {
        this.initializeActiveEnv();
        this.getEnhancedService();
      },
      immediate: true,
      deep: true,
    },
  },
  methods: {
    jumpToServices(item, type) {
      const params = {
        id: this.appCode,
        moduleId: this.activeModule,
      };
      if (type === 'detail' && item) {
        // service 跳转详情页需要携带的参数
        params.service = item.uuid;
      }
      this.$router.push({
        name: 'appServices',
        params,
      });
    },
    initializeActiveEnv() {
      this.activeModule = this.curAppModuleList[0]?.name || 'default';
    },
    // 获取增强服务列表
    async getEnhancedService() {
      this.isLoading = true;
      try {
        const ret = await this.$store.dispatch('service/getServicesList', {
          appCode: this.appCode,
          moduleId: this.activeModule,
          serviceId: 1,
        });
        this.processServiceData(ret);
      } catch (err) {
        this.catchErrorHandler(err);
      } finally {
        this.isLoading = false;
      }
    },
    processServiceData(data = {}) {
      const { bound = [], shared = [], unbound = [] } = data;

      // 合并已绑定和共享的服务作为已启用服务
      const boundServices = bound.map((item) => item.service);
      const sharedServices = shared.map((item) => ({
        ...item.service,
        type: 'shared',
      }));
      this.enabledServices = [...boundServices, ...sharedServices];

      // 未绑定的服务作为未启用服务
      this.unenabledServices = [...unbound];
    },
  },
};
</script>

<style lang="scss" scoped>
.service-items-container {
  .service-items {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(238px, 315px));
    gap: 10px;
  }
}
</style>
