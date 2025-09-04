<template>
  <div class="visible-range card-style">
    <section class="main">
      <div>
        <span
          class="title"
          v-bk-tooltips="{ content: $t('仅影响 蓝鲸桌面 上应用的可见范围') }"
          v-dashed
        >
          {{ $t('可见范围') }}
        </span>
      </div>
      <div class="content">
        <div class="top-wrapper">
          <!-- 多租户组织架构选择器 -->
          <bk-org-selector
            v-if="isMultiTenantDisplayMode"
            v-model="orgMemberSelector"
            :api-base-url="tenantApiBaseUrl"
            :tenant-id="tenantId"
            :has-user="true"
            @change="handleBkOrgSelector"
          ></bk-org-selector>
          <template v-else>
            <p
              class="info"
              v-if="departments.length === 0 && users.length === 0"
            >
              {{ $t('默认全员可见') }}
            </p>
            <p
              v-else
              class="info"
              v-dompurify-html="infoMsg"
            ></p>
            <div
              class="edit-container"
              @click="handleOpenMemberDialog"
            >
              <i class="paasng-icon paasng-edit-2 pl10" />
              {{ $t('编辑') }}
            </div>
          </template>
        </div>
        <!-- 组织/用户 -->
        <template v-if="!isMultiTenantDisplayMode">
          <div
            class="render-member-wrapper"
            v-if="departments.length || users.length"
          >
            <render-member-list
              v-if="departments.length > 0"
              type="department"
              :custom-styles="true"
              :data="departments"
            />
            <render-member-list
              v-if="users.length > 0"
              :custom-styles="true"
              :data="users"
            />
          </div>
        </template>
      </div>
    </section>

    <user-selector-dialog
      ref="userSelectorDialogRef"
      :show.sync="isShowUserSelector"
      :users="users"
      :departments="departments"
      :api-host="apiHost"
      :custom-close="true"
      @sumbit="handleSubmit"
    />
  </div>
</template>

<script>
import userSelectorDialog from '@/components/user-selector';
import RenderMemberList from './render-member-list';
import BkOrgSelector from '@blueking/bk-org-selector/vue2';
import { cloneDeep } from 'lodash';
import { PLATFORM_CONFIG } from '../../../../../static/json/paas_static';
import { mapGetters, mapState } from 'vuex';
import { normalizeOrgSelectionData } from '@/common/tools';
export default {
  name: 'AppVisibleRange',
  components: {
    userSelectorDialog,
    RenderMemberList,
    BkOrgSelector,
  },
  props: {
    data: {
      type: Object,
      default: () => {},
    },
  },
  data() {
    return {
      platFormConfig: PLATFORM_CONFIG,
      apiHost: window.BK_COMPONENT_API_URL,
      baseInfo: {},
      isShowUserSelector: false,
      orgMemberSelector: [],
    };
  },
  computed: {
    ...mapGetters(['tenantId', 'tenantApiBaseUrl', 'isMultiTenantDisplayMode']),
    appCode() {
      return this.$route.params.id;
    },
    users() {
      return (this.baseInfo.visiable_labels || []).filter((item) => item.type === 'user');
    },
    departments() {
      return (this.baseInfo.visiable_labels || []).filter((item) => item.type === 'department');
    },
    infoMsg() {
      return this.$t('已选择 <span>{d}</span> 个组织，<span class="s2">{s}</span> 个用户', {
        d: this.departments.length,
        s: this.users.length,
      });
    },
  },
  watch: {
    data: {
      handler(newVal) {
        this.baseInfo = cloneDeep(newVal);
        this.orgMemberSelector = normalizeOrgSelectionData(newVal?.visiable_labels || [], { nonUserType: 'org' });
      },
      deep: true,
      immediate: true,
    },
  },
  methods: {
    handleOpenMemberDialog() {
      this.isShowUserSelector = true;
    },
    handleSubmit(payload) {
      this.baseInfo.visiable_labels = payload;
      this.saveVisibleRange();
    },
    // 保存可见范围
    async saveVisibleRange(visiableLabels = []) {
      try {
        await this.$store.dispatch('market/updateMarketInfo', {
          appCode: this.appCode,
          data: {
            visiable_labels: this.isMultiTenantDisplayMode ? visiableLabels : this.baseInfo.visiable_labels,
          },
        });
        this.$paasMessage({
          theme: 'success',
          message: this.$t('保存成功！'),
        });
        this.$refs.userSelectorDialogRef?.handleCancel();
        this.$emit('get-app-info');
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      }
    },
    // 多租户组织架构选择
    handleBkOrgSelector(data) {
      const visiableLabels = normalizeOrgSelectionData(data);
      this.saveVisibleRange(visiableLabels);
    },
  },
};
</script>

<style lang="scss" scoped>
.visible-range {
  padding: 12px 24px;
  font-size: 14px;
  .main {
    display: flex;
    .title {
      font-weight: 700;
      font-size: 14px;
      color: #313238;
    }
    .content {
      margin-left: 24px;
      .top-wrapper {
        display: flex;
      }
      .edit-container {
        font-size: 14px;
        color: #3a84ff;
        cursor: pointer;
      }
      .render-member-wrapper {
        margin-top: 12px;
        padding: 12px 12px 12px 36px;
        width: 320px;
        background: #f5f7fa;
        border-radius: 2px;
      }
    }
    :deep(.info) {
      span {
        font-weight: 700;
        color: #2bcd56;
        &.s2 {
          color: #fda304;
        }
      }
    }
  }
}
</style>
