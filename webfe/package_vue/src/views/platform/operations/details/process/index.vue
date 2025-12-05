<template>
  <div
    class="process-container"
    v-bkloading="{ isLoading, zIndex: 10 }"
  >
    <bk-alert
      class="mb-16"
      type="warning"
      :title="
        $t(
          '在 S-mart 应用中，您在配置页面设置的资源配额将覆盖源码包中的应用描述文件（app_desc.yaml）所定义的配额。修改后，重新部署即可立即生效。'
        )
      "
    ></bk-alert>
    <!-- 模块、进程选择 -->
    <ProcessFilter
      :module-list="moduleList"
      :process-list="processList"
      :cur-module.sync="curModule"
      :cur-process.sync="curProcess"
      :loading="isProcessLoading"
      @module-change="handleModuleChange"
      @process-change="handleProcessChange"
    />
    <!-- 未部署 -->
    <section
      v-if="!processList.length && !isLoading"
      class="empty-process card-style"
    >
      <bk-exception type="empty">
        <span class="title">{{ $t('当前模块未部署，无法获取进程列表') }}</span>
      </bk-exception>
    </section>
    <!-- 资源配额 -->
    <ResourceQuota
      v-else
      :module-id="curModule"
      :process-data="curProcessData"
      @update="fetchProcessList"
    />
  </div>
</template>

<script>
import ProcessFilter from './process-filter';
import ResourceQuota from './resource-quota';

export default {
  name: 'ProcessManagement',
  components: {
    ProcessFilter,
    ResourceQuota,
  },
  data() {
    return {
      isLoading: false,
      isProcessLoading: false,
      curModule: '',
      moduleList: [],
      curProcess: '',
      processList: [],
    };
  },
  computed: {
    appCode() {
      return this.$route.params.code;
    },
    curProcessData() {
      return this.processList.find((item) => item.name === this.curProcess);
    },
  },
  async created() {
    this.isLoading = true;
    await this.fetchModuleList();
    await this.fetchProcessList();
    this.isLoading = false;
  },
  methods: {
    // 获取模块列表
    async fetchModuleList() {
      try {
        const ret = await this.$store.dispatch('tenantOperations/getAppDetails', {
          appCode: this.appCode,
        });
        // 主模块放在前面
        this.moduleList = ret.modules_info?.sort((a, b) => b.is_default - a.is_default) || [];
        this.curModule = this.moduleList[0]?.name || 'default';
      } catch (err) {
        this.catchErrorHandler(err);
      }
    },
    // 获取进程列表
    async fetchProcessList() {
      this.isProcessLoading = true;
      try {
        const ret = await this.$store.dispatch('tenantOperations/getProcesses', {
          appCode: this.appCode,
          moduleId: this.curModule,
        });
        this.processList = ret?.processes || [];
        if (!this.curProcess) {
          this.curProcess = this.processList[0]?.name || '';
        }
      } catch (err) {
        this.catchErrorHandler(err);
      } finally {
        this.isLoading = false;
        this.isProcessLoading = false;
      }
    },
    // 模块变更
    handleModuleChange(value) {
      this.curProcess = ''; // 切换模块时清空当前进程
      this.fetchProcessList();
    },
    // 进程切换
    handleProcessChange(processId) {
      this.curProcess = processId;
    },
  },
};
</script>

<style lang="scss" scoped>
.process-container {
  .empty-process {
    height: 600px;
    display: flex;
    align-items: center;
    justify-content: center;
    .title {
      font-size: 20px;
    }
  }
  .process-content {
    background: #fff;
    padding: 24px;
    min-height: 400px;
  }
}
</style>
