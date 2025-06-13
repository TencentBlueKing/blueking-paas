<template>
  <div class="code-repo">
    <bk-form
      ref="repoInfo"
      :label-width="100"
      :model="info"
    >
      <template v-if="type === 'bare_git'">
        <bk-form-item
          :label="$t('源代码地址')"
          :required="edited"
          :property="'url'"
          :rules="rules.gitUrl"
          :error-display-type="'normal'"
        >
          <bk-input
            v-if="edited"
            ref="url"
            v-model="info.url"
            class="form-input-width"
            :placeholder="`${$t('支持以下协议：')}http(s)://、git://`"
          />
          <p v-else>
            {{ info.url }}
          </p>
        </bk-form-item>
      </template>
      <template v-else>
        <bk-form-item
          :label="$t('源代码地址')"
          :required="edited"
          :property="'url'"
          :rules="rules.svnUrl"
          :error-display-type="'normal'"
        >
          <bk-input
            v-if="edited"
            ref="url"
            v-model="info.url"
            class="form-input-width"
            :placeholder="`${$t('支持以下协议：')}http(s)://、svn://，${$t('并确保trunk、branches、tags等在该目录下')}`"
          />
          <p v-else>
            {{ info.url }}
          </p>
        </bk-form-item>
      </template>

      <!-- 普通应用 -->
      <bk-form-item
        v-if="deploymentIsShow && !isCloudCreated"
        :class="{ mt15: !edited }"
        :label="$t(sourceDirLabel)"
        :desc="sourceDirTip"
        :property="'sourceDir'"
        :rules="rules.sourceDir"
        :error-display-type="'normal'"
      >
        <bk-input
          v-if="edited"
          ref="sourceDir"
          class="form-input-width"
          v-model="info.sourceDir"
        />
        <p v-else>
          {{ info.sourceDir }}
        </p>
      </bk-form-item>

      <bk-form-item
        :class="{ mt15: !edited }"
        :label="accountLabel"
        :required="edited"
        :property="'account'"
        :rules="rules.account"
        :error-display-type="'normal'"
      >
        <bk-input
          v-if="edited"
          ref="account"
          class="form-input-width"
          v-model="info.account"
        />
        <p v-else>
          {{ info.account }}
        </p>
      </bk-form-item>
      <bk-form-item
        :class="{ mt15: !edited }"
        :label="$t('密码')"
        :required="edited"
        :property="'password'"
        :rules="rules.password"
        :error-display-type="'normal'"
      >
        <bk-input
          v-if="edited"
          ref="password"
          v-model="info.password"
          class="form-input-width"
          type="password"
          :placeholder="$t('请输入')"
        />
        <p v-else>******</p>
      </bk-form-item>

      <!-- 云原生应用 -->
      <bk-form-item
        v-if="deploymentIsShow && isCloudCreated"
        :class="[{ mt15: !edited }]"
        :label="$t(sourceDirLabel)"
        :property="'sourceDir'"
        :rules="rules.sourceDir"
        :error-display-type="'normal'"
      >
        <bk-input
          v-if="edited"
          ref="sourceDir"
          class="form-input-width"
          v-model="info.sourceDir"
          :placeholder="$t('请输入应用所在子目录，不填则默认为根目录')"
        />
        <p v-else>
          {{ info.sourceDir }}
        </p>
      </bk-form-item>
    </bk-form>
  </div>
</template>

<script>
export default {
  props: {
    edited: {
      type: Boolean,
      default: true,
    },
    type: {
      type: String,
      default: 'bare_git',
    },
    defaultUrl: {
      type: String,
      default: '',
    },
    defaultAccount: {
      type: String,
      default: '',
    },
    defaultPassword: {
      type: String,
      default: '',
    },
    defaultDir: {
      type: String,
      default: '',
    },
    deploymentIsShow: {
      type: Boolean,
      default: true,
    },
    sourceDirLabel: {
      type: String,
      default: '部署目录',
    },
    isCloudCreated: {
      type: Boolean,
      default: false,
    },
  },
  data() {
    return {
      info: {
        url: this.defaultUrl,
        account: this.defaultAccount,
        password: this.defaultPassword,
        sourceDir: this.defaultDir,
      },
      rules: {
        gitUrl: [
          {
            required: true,
            message: this.$t('该字段是必填项'),
            trigger: 'blur',
          },
          {
            // http(s)://、git://
            regex: /^(http|https|git):\/\//,
            message: `${this.$t('请输入正确源代码地址，支持以下协议')}：http(s)://、git://`,
            trigger: 'blur',
          },
        ],
        svnUrl: [
          {
            required: true,
            message: this.$t('该字段是必填项'),
            trigger: 'blur',
          },
          {
            // http(s)://、svn://
            regex: /^(http|https|svn):\/\//,
            message: `${this.$t('请输入正确源代码地址，支持以下协议')}：http(s)://、svn://`,
            trigger: 'blur',
          },
        ],
        sourceDir: [
          {
            regex: /^((?!\.)[a-zA-Z0-9_./-]+|\s*)$/,
            message: this.$t(
              '支持子目录、如 ab/test，允许字母、数字、点(.)、下划线(_)、和连接符(-)，但不允许以点(.)开头'
            ),
            trigger: 'blur',
          },
        ],
        account: [
          {
            required: true,
            message: this.$t('该字段是必填项'),
            trigger: 'blur',
          },
        ],
        password: [
          {
            required: true,
            message: this.$t('该字段是必填项'),
            trigger: 'blur',
          },
        ],
      },
      sourceDirTip: {
        theme: 'light',
        allowHtml: true,
        content: this.$t('提示信息'),
        html: `<a target="_blank" href="${this.GLOBAL.DOC.DEPLOY_DIR}" style="color: #3a84ff">${this.$t(
          '如何设置部署目录'
        )}</a>`,
        placements: ['right'],
      },
    };
  },
  computed: {
    accountLabel() {
      return this.type === 'bare_git' ? this.$t('Git账号') : this.$t('SVN账号');
    },
  },
  watch: {
    type() {
      this.info = {
        url: '',
        account: '',
        password: '',
        sourceDir: '',
      };
    },
    info: {
      deep: true,
      handler() {
        const data = this.getData();
        this.$emit('change', data);
      },
    },
    edited(v) {
      if (!v) {
        this.info = {
          url: this.defaultUrl,
          account: this.defaultAccount,
          password: '',
          sourceDir: this.defaultDir,
        };
      }
    },
    'info.sourceDir'(newVal) {
      this.$emit('dir-change', newVal);
    },
  },
  methods: {
    async validate(callback) {
      this.$refs.repoInfo
        .validate()
        .then(() => {
          callback && callback();
        })
        .catch((error) => {
          const { field } = error;
          this.$refs[field].focus();
        });
    },

    async valid() {
      try {
        const validRet = await this.$refs.repoInfo.validate();
        return validRet;
      } catch (error) {
        const { field } = error;
        this.$refs[field].focus();
        return Promise.reject(error);
      }
    },

    getData() {
      const gitUrlReg = /^(http|https|git):\/\//;
      const svnUrlReg = /^(http|https|svn):\/\//;
      let url = '';
      if (this.type === 'bare_git') {
        if (gitUrlReg.test(this.info.url)) {
          url = this.info.url;
        }
      } else {
        if (svnUrlReg.test(this.info.url)) {
          url = this.info.url;
        }
      }

      return {
        url,
        account: this.info.account,
        password: this.info.password,
        sourceDir: this.info.sourceDir,
      };
    },
  },
};
</script>

<style lang="scss" scoped>
.form-input-width {
  width: 650px;
}
</style>
