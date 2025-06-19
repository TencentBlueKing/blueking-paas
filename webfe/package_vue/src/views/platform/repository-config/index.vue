<template>
  <div class="repository-config-container p-24">
    <bk-alert
      type="warning"
      :title="$t('修改代码库配置，需要重启 apiserver-web、apiserver-worker进程才有效。 ')"
    ></bk-alert>
    <div class="top-box mt-16">
      <bk-button
        :theme="'primary'"
        class="mr10"
        icon="plus"
        @click="handleShowRepository('add')"
      >
        {{ $t('代码库配置') }}
      </bk-button>
    </div>
    <bk-table
      ref="tableRef"
      :data="repositoryList"
      size="small"
      class="plan-table-cls mt-16"
      v-bkloading="{ isLoading: isTableLoading, zIndex: 10 }"
    >
      <bk-table-column
        v-for="column in columns"
        v-bind="column"
        :label="$t(column.label)"
        :prop="column.prop"
        :key="column.prop"
        show-overflow-tooltip
      >
        <template slot-scope="{ row }">
          <span
            :class="['tag', { yes: row.enabled }]"
            v-if="column.prop === 'enabled'"
          >
            {{ row.enabled ? $t('是') : $t('否') }}
          </span>
          <span v-else>{{ row[column.prop] || '--' }}</span>
        </template>
      </bk-table-column>
      <bk-table-column
        :label="$t('操作')"
        :width="200"
      >
        <template slot-scope="{ row }">
          <bk-button
            theme="primary"
            text
            class="mr10"
            @click="handleShowDetail(row)"
          >
            {{ $t('查看详情') }}
          </bk-button>
          <bk-button
            theme="primary"
            text
            class="mr10"
            @click="handleShowRepository('edit', row)"
          >
            {{ $t('编辑') }}
          </bk-button>
          <bk-button
            theme="primary"
            text
            @click="handleShowDelDialog(row)"
          >
            {{ $t('删除') }}
          </bk-button>
        </template>
      </bk-table-column>
    </bk-table>

    <!-- 代码库配置 -->
    <RepositorySideslider
      :show.sync="repositorySideConfig.isShow"
      :data="repositorySideConfig.row"
      :type="repositorySideConfig.type"
      @refresh="getSourceTypeSpec"
    />

    <!-- 详情 -->
    <DetailSideslider
      :show.sync="detailSideConfig.isShow"
      :name="detailSideConfig.name"
    />

    <!-- 删除代码仓库配置 -->
    <bk-dialog
      v-model="deleteDialogConfig.visible"
      width="480"
      theme="primary"
      :mask-close="false"
      :auto-close="false"
      header-position="left"
      :title="$t('确认删除该代码库配置？')"
      :ok-text="$t('删除')"
      :loading="deleteDialogConfig.loading"
      @confirm="deleteRepositoryConfig"
    >
      <div class="f12">
        {{ `${$t('服务名称')}：` }}
        <span style="color: #313238">{{ deleteDialogConfig.name }}</span>
      </div>
      <p class="f12 mt-4">{{ $t('删除后，应用将不能再使用这种类型的代码仓库。') }}</p>
    </bk-dialog>
  </div>
</template>

<script>
import RepositorySideslider from './repository-sideslider.vue';
import DetailSideslider from './detail-sideslider.vue';

export default {
  name: 'RepositoryConfig',
  components: {
    RepositorySideslider,
    DetailSideslider,
  },
  data() {
    return {
      repositoryList: [],
      isTableLoading: false,
      columns: [
        {
          label: '服务名称',
          prop: 'name',
        },
        {
          label: '标签（中文）',
          prop: 'label_zh_cn',
        },
        {
          label: '标签（英文）',
          prop: 'label_en',
        },
        {
          label: '是否默认开放',
          prop: 'enabled',
          'render-header': this.renderHeader,
        },
        {
          label: 'ClientID',
          prop: 'client_id',
        },
      ],
      repositorySideConfig: {
        isShow: false,
        type: 'add',
        row: {},
      },
      detailSideConfig: {
        isShow: false,
        name: '',
      },
      deleteDialogConfig: {
        visible: false,
        loading: false,
        name: '',
      },
    };
  },
  created() {
    this.getSourceTypeSpec();
  },
  methods: {
    // 租户id/资源配额自定义表头
    renderHeader(h, data) {
      const directive = {
        name: 'bkTooltips',
        content: this.$t(
          '关闭后，用户将无法创建与该源码类型仓库关联的新应用，可以通过“用户特性”为特定用户单独开启此功能。'
        ),
        placement: 'top',
        width: 220,
      };
      return (
        <span
          class="custom-header-cell"
          v-bk-tooltips={directive}
        >
          {data.column.label}
        </span>
      );
    },
    // 获取代码库配置列表
    async getSourceTypeSpec() {
      this.isTableLoading = true;
      try {
        const res = await this.$store.dispatch('tenantConfig/getSourceTypeSpec');
        this.repositoryList = res;
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.isTableLoading = false;
      }
    },
    // 获取代码库详情
    async getRepositoryDetail(name) {
      try {
        const ret = await this.$store.dispatch('tenantConfig/getRepositoryDetail', {
          name,
        });
        this.repositorySideConfig.row = ret;
      } catch (e) {
        this.catchErrorHandler(e);
      }
    },
    // 删除代码库配置
    async deleteRepositoryConfig() {
      this.deleteDialogConfig.loading = true;
      try {
        await this.$store.dispatch('tenantConfig/deleteRepositoryConfig', {
          name: this.deleteDialogConfig.name,
        });
        this.$paasMessage({
          theme: 'success',
          message: this.$t('删除成功'),
        });
        this.toggleDeleteDialog(false);
        this.getSourceTypeSpec();
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.deleteDialogConfig.loading = false;
      }
    },
    showRepository() {
      this.repositorySideConfig.isShow = true;
    },
    handleShowRepository(type, row) {
      this.repositorySideConfig.type = type;
      this.showRepository();
      if (type === 'edit') {
        this.getRepositoryDetail(row.name);
      }
    },
    toggleDeleteDialog(visible) {
      this.deleteDialogConfig.visible = visible;
    },
    handleShowDelDialog(row) {
      this.toggleDeleteDialog(true);
      this.deleteDialogConfig.name = row.name;
    },
    // 查看详情
    handleShowDetail(row) {
      this.detailSideConfig.isShow = true;
      this.detailSideConfig.name = row.name;
    },
  },
};
</script>

<style lang="scss" scoped>
.repository-config-container {
  /deep/ .bk-table-header {
    .custom-header-cell {
      text-decoration: underline;
      text-decoration-style: dashed;
      text-underline-position: under;
    }
  }
}
</style>
