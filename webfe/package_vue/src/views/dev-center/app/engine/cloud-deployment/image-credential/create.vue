<template>
  <div>
    <bk-dialog
      v-model="versionDialogConf.visiable"
      :title="versionDialogConf.title"
      header-position="center"
      :width="600"
      @after-leave="handleCancel"
    >
      <bk-form
        ref="versionForm"
        class="mt20 mb10"
        style="width: 540px;"
        :label-width="localLanguage === 'en' ? 100 : 80"
        :model="crdlParams"
        :rules="rules"
      >
        <bk-form-item
          :label="$t('名称')"
          :required="true"
          :property="'name'"
        >
          <bk-input
            v-model="crdlParams.name"
            :placeholder="$t('以英文字母、数字或下划线(_)组成，不超过40个字')"
            :disabled="type === 'edit'"
          />
        </bk-form-item>
        <bk-form-item
          :label="$t('账号')"
          :required="true"
          :property="'username'"
        >
          <bk-input
            v-model="crdlParams.username"
            :placeholder="$t('请输入')"
          />
        </bk-form-item>
        <bk-form-item
          :label="$t('密码')"
          :required="true"
          :property="'password'"
        >
          <bk-input
            v-model="crdlParams.password"
            ext-cls="passwordEl"
            type="password"
            :placeholder="$t('请输入')"
            autocomplete="off"
          />
          <!-- <p v-else>******</p> -->
        </bk-form-item>
        <bk-form-item
          :label="$t('描述')"
          :property="'description'"
        >
          <bk-input
            v-model="crdlParams.description"
            type="textarea"
            :maxlength="500"
            :placeholder="$t('描述')"
          />
        </bk-form-item>
      </bk-form>
      <div slot="footer">
        <bk-button
          theme="primary"
          :loading="versionDialogConf.loading"
          @click="handleCreate"
        >
          {{ $t('确定') }}
        </bk-button>
        <bk-button class="ml8" @click="handleCancel">
          {{ $t('取消') }}
        </bk-button>
      </div>
    </bk-dialog>
  </div>
</template>

<script>
import i18n from '@/language/i18n.js';
export default {
  props: {
    config: {
      type: Object,
      default: () => {},
    },
    type: {
      type: String,
      default: 'new',
    },
    credentialDetail: {
      type: Object,
      default: () => {},
    },
  },
  data() {
    return {
      isDataLoading: false,
      crdlParams: {
        name: '',
        username: '',
        password: '',
        description: '',
      },
      versionDialogConf: {
        loading: false,
        visiable: false,
        title: i18n.t('新增凭证'),
      },
      isShowPassword: false,
      rules: {
        name: [
          {
            required: true,
            message: i18n.t('请填写名称'),
            trigger: 'blur',
          },
          {
            regex: /^[a-zA-Z0-9_]{0,40}$|^$/,
            message: i18n.t('以英文字母、数字或下划线(_)组成，不超过40个字'),
            trigger: 'blur',
          },
        ],
        username: [
          {
            required: true,
            message: i18n.t('该字段不能为空'),
            trigger: 'blur',
          },
        ],
        password: [
          {
            required: true,
            message: i18n.t('该字段不能为空'),
            trigger: 'blur',
          },
        ],
      },
    };
  },

  computed: {
    appCode() {
      return this.$route.params.id;
    },
    localLanguage() {
      return this.$store.state.localLanguage;
    },
  },

  watch: {
    type(newVal) {
      this.type = newVal;
    },
    credentialDetail(newVal) {
      if (Object.keys(newVal).length) {
        this.crdlParams = newVal;
      }
    },
  },

  created() {
    this.init();
  },

  mounted() {
    this.setAutocomplete();
  },

  methods: {
    init() {
      this.versionDialogConf = this.config;
    },

    // 新增凭证
    handleCreate() {
      // 表单校验，通过传递数据
      this.$refs.versionForm.validate().then((validator) => {
        if (this.type === 'new') {
          this.$emit('confirm', this.crdlParams);
        } else {
          this.$emit('updata', this.crdlParams);
        }
      }, err => err);
    },

    handleCancel() {
      this.crdlParams = {
        name: '',
        username: '',
        password: '',
        description: '',
      };
      this.$refs.versionForm.clearError();
      this.$emit('close', false);
    },

    setAutocomplete() {
      document.querySelector('.passwordEl input').setAttribute('autocomplete', 'off');
    },
  },
};
</script>

<style scoped lang="postcss">

</style>
