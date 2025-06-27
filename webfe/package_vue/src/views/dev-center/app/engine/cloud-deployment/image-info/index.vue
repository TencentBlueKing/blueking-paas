<template>
  <div class="image-info-container">
    <div class="base-info-container">
      <div class="flex-row align-items-center">
        <span class="base-info-title">
          {{ $t('基本信息-title') }}
        </span>
        <div
          class="edit-container"
          @click="handleEdit('isBasePageEdit')"
          v-if="!isBasePageEdit"
        >
          <i class="paasng-icon paasng-edit-2 pl10" />
          {{ $t('编辑') }}
        </div>
      </div>
      <div
        class="form-detail mt20 pb20 border-b"
        v-if="!isBasePageEdit"
      >
        <bk-form :model="buildConfig">
          <bk-form-item :label="`${$t('托管方式')}：`">
            <span class="form-text">{{ artifactType || '--' }}</span>
          </bk-form-item>
          <bk-form-item :label="`${$t('镜像仓库')}：`">
            <span class="form-text">{{ buildConfig.image_repository || '--' }}</span>
          </bk-form-item>
          <bk-form-item :label="`${$t('镜像凭证')}：`">
            <span class="form-text">{{ buildConfig.image_credential_name || '--' }}</span>
          </bk-form-item>
        </bk-form>
      </div>

      <div
        class="form-edit mt20 pb20 border-b"
        v-if="isBasePageEdit"
      >
        <bk-form
          :model="buildConfig"
          ref="baseInfoRef"
        >
          <bk-form-item :label="`${$t('托管方式')}：`">
            <span class="form-text">{{ artifactType || '--' }}</span>
          </bk-form-item>

          <bk-form-item
            :label="`${$t('镜像仓库')}：`"
            :required="true"
            :property="'image_repository'"
            :rules="rules.image"
            error-display-type="normal"
          >
            <bk-input
              ref="imageRef"
              v-model="buildConfig.image_repository"
              style="width: 450px"
              :placeholder="$t('请输入镜像仓库，如') + '：mirrors.tencent.com/bkpaas/django-helloworld'"
            ></bk-input>
            <p
              slot="tip"
              class="input-tips"
            >
              {{ $t('一个模块只可以配置一个镜像仓库，"进程配置"中的所有进程都会使用该镜像。') }}
            </p>
          </bk-form-item>

          <bk-form-item :label="`${$t('镜像凭证')}：`">
            <bk-select
              v-model="buildConfig.image_credential_name"
              style="width: 450px"
              searchable
            >
              <bk-option
                v-for="option in credentialList"
                :id="option.name"
                :key="option.name"
                :name="option.name"
              />
            </bk-select>
          </bk-form-item>
        </bk-form>

        <div class="ml150">
          <bk-button
            theme="primary"
            title="保存"
            class="mt20"
            @click="handleSave"
          >
            {{ $t('保存') }}
          </bk-button>

          <bk-button
            :theme="'default'"
            title="取消"
            class="mt20 ml8"
            @click="handleCancel"
          >
            {{ $t('取消') }}
          </bk-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import appBaseMixin from '@/mixins/app-base-mixin.js';
import { cloneDeep } from 'lodash';
export default {
  name: 'ImageBaseInfo',
  mixins: [appBaseMixin],
  props: {
    credentialList: {
      type: Array,
      default: () => [],
    },
  },
  data() {
    return {
      isBasePageEdit: false,
      buildConfig: {},
      buildConfigClone: {},
      rules: {
        image: [
          {
            required: true,
            message: this.$t('该字段是必填项'),
            trigger: 'blur',
          },
          {
            regex: /^(?:([a-zA-Z0-9]+(?:[._-][a-zA-Z0-9]+)*(?::\d+)?)\/)?(?:([a-zA-Z0-9_-]+)\/)*([a-zA-Z0-9_.-]+)$/,
            message: this.$t('请输入不包含标签(tag)的镜像仓库地址'),
            trigger: 'blur',
          },
        ],
      },
    };
  },
  computed: {
    artifactType() {
      if (this.buildConfig.build_method === 'custom_image') {
        return this.$t('仅镜像');
      }
      if (this.buildConfig.build_method === 'slug') {
        return this.$t('仅源码');
      }
      return this.$t('源代码');
    },
    // 基本信息是否为编辑态
    isModuleInfoEdit() {
      return this.$store.state.cloudApi.isModuleInfoEdit;
    },
  },
  created() {
    // 获取基本信息
    this.getBaseInfo();
  },
  mounted() {
    // 默认为编辑态
    this.isModuleInfoEdit && this.handleEdit('isBasePageEdit');
  },
  beforeDestroy() {
    this.$store.commit('cloudApi/updateModuleInfoEdit', false);
  },
  methods: {
    // 获取info信息
    async getBaseInfo() {
      try {
        const res = await this.$store.dispatch('deploy/getAppBuildConfigInfo', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
        });
        this.buildConfig = { ...res };
        if (this.buildConfig.image_credential_name === null) {
          this.buildConfig.image_credential_name = '';
        }
        this.buildConfigClone = cloneDeep(this.buildConfig);
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message,
        });
      }
    },

    async handleSave() {
      // 基本信息页面保存
      if (this.isBasePageEdit) {
        try {
          await this.$refs.baseInfoRef.validate();
          if (this.buildConfig.image_credential_name === '') {
            this.buildConfig.image_credential_name = null;
          }
          await this.$store.dispatch('deploy/SaveAppBuildConfigInfo', {
            appCode: this.appCode,
            moduleId: this.curModuleId,
            params: { ...this.buildConfig },
          });
          this.getBaseInfo();
          this.$paasMessage({
            theme: 'success',
            message: this.$t('操作成功'),
          });
          this.$refs.baseInfoRef?.clearError();
          this.isBasePageEdit = false;
        } catch (e) {
          console.error(e);
        }
      }
    },

    // 编辑
    handleEdit(value) {
      this[value] = true;
      this.$nextTick(() => {
        this.$refs.imageRef?.focus();
      });
    },

    // 取消
    handleCancel() {
      this.isDeployLimitEdit = false;
      this.isIpInfoEdit = false;
      if (this.isBasePageEdit) {
        this.buildConfig = cloneDeep(this.buildConfigClone);
        this.isBasePageEdit = false;
      }
      this.$refs.baseInfoRef?.clearError();
    },
  },
};
</script>

<style lang="scss" scoped>
.image-info-container {
  border-bottom: 1px solid #dcdee5;
  .base-info-title {
    color: #313238;
    font-size: 14px;
    font-weight: bold;
    text-align: right;
  }
  .edit-container {
    color: #3a84ff;
    font-size: 12px;
    cursor: pointer;
    padding-left: 10px;
  }
  .ml150 {
    margin-left: 150px;
  }
}
</style>
