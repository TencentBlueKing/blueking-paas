<template>
  <div class="repository-config-container p-24">
    <bk-alert
      type="warning"
      :title="$t('代码库配置变更后，需重启 apiserver 所有进程才会生效。')"
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
      :id="repositorySideConfig.id"
      @refresh="getSourceTypeSpec"
    />

    <!-- 详情 -->
    <DetailSideslider
      :show.sync="detailSideConfig.isShow"
      :id="detailSideConfig.id"
    />

    <!-- 删除代码仓库配置 -->
    <DeleteDialog
      :show.sync="deleteDialogConfig.visible"
      :title="$t('确认删除代码库配置')"
      :expected-confirm-text="deleteDialogConfig.row.name"
      :loading="deleteDialogConfig.loading"
      @confirm="deleteRepositoryConfig"
    >
      <div class="hint-text">
        <p>{{ $t('删除后，应用将无法使用此类型的代码库，已使用该代码库的应用也无法部署。') }}</p>
        <span>{{ $t('请输入要删除的代码库的服务名称') }}</span>
        <span>
          （
          <span class="sign">{{ deleteDialogConfig.row.name }}</span>
          <i
            class="paasng-icon paasng-general-copy"
            v-copy="deleteDialogConfig.row.name"
          />
          ）
        </span>
        {{ $t('进行确认') }}
      </div>
    </DeleteDialog>
  </div>
</template>

<script>
import RepositorySideslider from './repository-sideslider.vue';
import DetailSideslider from './detail-sideslider.vue';
import DeleteDialog from '@/components/delete-dialog';

export default {
  name: 'RepositoryConfig',
  components: {
    RepositorySideslider,
    DetailSideslider,
    DeleteDialog,
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
      ],
      repositorySideConfig: {
        isShow: false,
        type: 'add',
        row: {},
        id: -1,
      },
      detailSideConfig: {
        isShow: false,
        id: -1,
      },
      deleteDialogConfig: {
        visible: false,
        loading: false,
        row: {},
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
    async getRepositoryDetail(id) {
      try {
        this.repositorySideConfig.id = id;
        const ret = await this.$store.dispatch('tenantConfig/getRepositoryDetail', {
          id,
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
          id: this.deleteDialogConfig.row.id,
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
        this.getRepositoryDetail(row.id);
      }
    },
    toggleDeleteDialog(visible) {
      this.deleteDialogConfig.visible = visible;
    },
    handleShowDelDialog(row) {
      this.toggleDeleteDialog(true);
      this.deleteDialogConfig.row = row;
    },
    // 查看详情
    handleShowDetail(row) {
      this.detailSideConfig.isShow = true;
      this.detailSideConfig.id = row.id;
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
