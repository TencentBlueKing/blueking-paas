<template>
  <div class="right-main p-24">
    <div class="top-box">
      <bk-button
        :theme="'primary'"
        class="mr10"
        icon="plus"
        @click="handleShowRepository('add')"
      >
        {{ $t('模版配置') }}
      </bk-button>
    </div>
    <bk-table
      ref="tableRef"
      :data="displayTemplateList"
      size="small"
      class="plan-table-cls mt-16"
      v-bkloading="{ isLoading: isTableLoading, zIndex: 10 }"
      @filter-change="handleFilterChange"
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
            :class="['tag', { yes: row.is_display }]"
            v-if="column.prop === 'is_display'"
          >
            {{ row.is_display ? $t('是') : $t('否') }}
          </span>
          <span v-else-if="column.prop === 'type'">
            {{ templateTypeMap[row.type] }}
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
    <TemplateSideslider
      :show.sync="templateSideConfig.isShow"
      :data="curTemplateDetail"
      :type="templateSideConfig.type"
      :id="templateSideConfig.id"
      :metadata="templateMetadata"
      @refresh="getTemplates"
    />

    <!-- 详情 -->
    <DetailSide
      :show.sync="detailSideConfig.isShow"
      :title="$t('模版配置')"
      :panels="panels"
      :width="690"
    >
      <div
        v-bkloading="{ isLoading: detailSideConfig.loading, zIndex: 10 }"
        slot-scope="{ active }"
      >
        <Detail
          :data="curTemplateDetail"
          :tab-active="active"
        />
      </div>
    </DetailSide>

    <!-- 删除 -->
    <DeleteDialog
      :show.sync="deleteDialogConfig.visible"
      :title="$t('确认删除模版配置')"
      :expected-confirm-text="deleteDialogConfig.row.name"
      :loading="deleteDialogConfig.loading"
      @confirm="deleteTemplateConfig"
    >
      <div class="hint-text">
        <p>{{ $t('删除后，创建应用时将不能再使用该模版。') }}</p>
        <span>{{ $t('请输入要删除的模版配置的模版名称') }}</span>
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
import TemplateSideslider from './template-sideslider.vue';
import DetailSide from '../components/detail-side';
import Detail from './detail.vue';
import DeleteDialog from '@/components/delete-dialog';
import { mapState } from 'vuex';

export default {
  name: 'RepositoryConfig',
  components: {
    TemplateSideslider,
    DetailSide,
    Detail,
    DeleteDialog,
  },
  data() {
    return {
      templateList: [],
      isTableLoading: false,
      templateSideConfig: {
        isShow: false,
        type: 'add',
        id: -1,
      },
      // 详情侧栏
      detailSideConfig: {
        isShow: false,
        loading: false,
        type: 'normal',
      },
      deleteDialogConfig: {
        visible: false,
        loading: false,
        row: {},
      },
      curTemplateDetail: {},
      templateMetadata: {},
      filterValue: '',
      templateTypeMap: {},
    };
  },
  computed: {
    ...mapState(['localLanguage']),
    templateTypes() {
      return (
        this.templateMetadata.template_types?.map((v) => ({
          text: v.label,
          value: v.name,
        })) || []
      );
    },
    columns() {
      return [
        {
          label: '模版名称',
          prop: 'name',
        },
        {
          label: '展示名称',
          prop: this.localLanguage === 'en' ? 'display_name_en' : 'display_name_zh_cn',
        },
        {
          label: '模版类型',
          prop: 'type',
          columnKey: 'type',
          filters: this.templateTypes,
          filterMultiple: false,
        },
        {
          label: '开发语言',
          prop: 'language',
        },
        {
          label: '是否展示',
          prop: 'is_display',
        },
      ];
    },
    displayTemplateList() {
      if (!this.filterValue) {
        return this.templateList;
      }
      return this.templateList.filter((v) => v.type === this.filterValue);
    },
    panels() {
      return [
        { name: 'baseInfo', label: this.$t('基本信息') },
        { name: this.detailSideConfig.type === 'normal' ? 'default' : 'plugin', label: this.$t('模版信息') },
        { name: 'config', label: this.$t('配置信息') },
      ];
    },
  },
  created() {
    this.getTemplates();
    this.getTemplateMetadata();
  },
  methods: {
    // 表头筛选
    handleFilterChange(filds) {
      this.filterValue = filds.type?.[0] || '';
    },
    // 获取模版配置列表
    async getTemplates() {
      this.isTableLoading = true;
      try {
        const res = await this.$store.dispatch('tenantConfig/getTemplates');
        this.templateList = res;
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.isTableLoading = false;
      }
    },
    // 获取模版配置元数据
    async getTemplateMetadata() {
      try {
        const ret = await this.$store.dispatch('tenantConfig/getTemplateMetadata');
        this.templateTypeMap = (ret.template_types || []).reduce((obj, item) => {
          obj[item.name] = item.label;
          return obj;
        }, {});
        this.templateMetadata = ret;
      } catch (e) {
        this.catchErrorHandler(e);
      }
    },
    // 获取模版配置详情
    async getTemplateDetail(templateId) {
      this.detailSideConfig.loading = true;
      try {
        this.templateSideConfig.id = templateId;
        const ret = await this.$store.dispatch('tenantConfig/getTemplateDetail', {
          templateId,
        });
        this.curTemplateDetail = ret;
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.detailSideConfig.loading = false;
      }
    },
    // 删除模版配置
    async deleteTemplateConfig() {
      this.deleteDialogConfig.loading = true;
      try {
        await this.$store.dispatch('tenantConfig/deleteTemplateConfig', {
          templateId: this.deleteDialogConfig.row.id,
        });
        this.$paasMessage({
          theme: 'success',
          message: this.$t('删除成功'),
        });
        this.toggleDeleteDialog(false);
        this.getTemplates();
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.deleteDialogConfig.loading = false;
      }
    },
    handleShowRepository(type, row) {
      this.templateSideConfig.type = type;
      this.templateSideConfig.isShow = true;
      if (type === 'edit') {
        this.getTemplateDetail(row.id);
      }
    },
    toggleDeleteDialog(visible) {
      this.deleteDialogConfig.visible = visible;
    },
    // 删除模版配置
    handleShowDelDialog(row) {
      this.toggleDeleteDialog(true);
      this.deleteDialogConfig.row = row;
    },
    // 查看详情
    handleShowDetail(row) {
      this.detailSideConfig.isShow = true;
      this.detailSideConfig.type = row.type;
      this.getTemplateDetail(row.id);
    },
  },
};
</script>
