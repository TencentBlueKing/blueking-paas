<template>
  <div class="establish">
    <form
      id="form-create-app"
      data-test-id="createDefault_form_appInfo"
      @submit.stop.prevent="submitCreateForm"
    >
      <div class="ps-tip-block default-info mt15">
        <i
          style="color: #3A84FF;"
          class="paasng-icon paasng-info-circle"
        />
        {{ $t('平台为该类应用提供云 API 权限申请、应用市场等功能') }}
      </div>

      <!-- 基本信息 -->
      <div
        class="create-item"
        data-test-id="createDefault_item_baseInfo"
      >
        <div class="item-title">
          {{ $t('基本信息') }}
        </div>
        <div
          class="form-group"
          style="margin-top: 10px;"
        >
          <label class="form-label"> {{ $t('应用 ID') }} </label>
          <div class="form-group-flex">
            <p>
              <input
                type="text"
                autocomplete="off"
                name="code"
                data-parsley-required="true"
                :data-parsley-required-message="$t('该字段是必填项')"
                data-parsley-minlength="3"
                data-parsley-maxlength="16"
                data-parsley-pattern="[a-z][a-z0-9-]+"
                :data-parsley-pattern-message="$t('格式不正确，只能包含：3-16 字符的小写字母、数字、连字符(-)，以小写字母开头')"
                data-parsley-trigger="input blur"
                class="ps-form-control"
                :placeholder="$t('请输入 3-16 字符的小写字母、数字、连字符(-)，以小写字母开头')"
                @input="handleInput('code')"
              >
            </p>
            <p class="whole-item-tips">
              {{ $t('应用的唯一标识，创建后不可修改') }}
            </p>
          </div>
        </div>
        <div class="form-group">
          <label class="form-label"> {{ $t('应用名称') }} </label>
          <p class="form-group-flex">
            <input
              type="text"
              autocomplete="off"
              name="name"
              data-parsley-required="true"
              :data-parsley-required-message="$t('该字段是必填项')"
              data-parsley-maxlength="20"
              data-parsley-pattern="[a-zA-Z\d\u4e00-\u9fa5-]+"
              :data-parsley-pattern-message="$t('格式不正确，只能包含：汉字、英文字母、数字、连字符(-)，长度小于 20 个字符')"
              data-parsley-trigger="input blur"
              class="ps-form-control"
              :placeholder="$t('由汉字、英文字母、数字、连字符（-）组成，长度小于 20 个字符')"
              @input="handleInput('name')"
            >
          </p>
        </div>
        <div
          v-if="platformFeature.REGION_DISPLAY"
          class="form-group"
          style="margin-top: 7px;"
        >
          <label class="form-label"> {{ $t('应用版本') }} </label>
          <div
            v-for="region in regionChoices"
            :key="region.key"
            class="form-group-flex-radio"
          >
            <div class="form-group-radio">
              <bk-radio-group
                v-model="regionChoose"
                style="width: 72px;"
              >
                <bk-radio
                  :key="region.key"
                  :value="region.key"
                >
                  {{ region.value }}
                </bk-radio>
              </bk-radio-group>
              <p class="whole-item-tips">
                {{ region.description }}
              </p>
            </div>
          </div>
        </div>
      </div>

      <div
        class="create-item"
        data-test-id="createDefault_item_baseInfo"
      >
        <div class="item-title">
          {{ $t('应用市场') }}
        </div>
        <div
          class="form-group-dir"
          style="margin-top: 10px;"
        >
          <label class="form-label"> {{ $t('访问地址') }} </label>
          <div class="form-group-flex">
            <p>
              <input
                type="text"
                autocomplete="off"
                name="source_tp_url"
                :data-parsley-required-message="$t('该字段是必填项')"
                data-parsley-pattern="^((https|http|ftp|rtsp|mms)?:\/\/)[a-zA-Z0-9][-a-zA-Z0-9]{0,62}(\.[a-zA-Z0-9][-a-zA-Z0-9]{0,62})+(\/?[A-Za-z0-9+&@#/%=~_|-]+(\/?))*$"
                :data-parsley-pattern-message="$t('地址格式不正确')"
                data-parsley-trigger="input blur"
                class="ps-form-control"
                :placeholder="$t('请输入正确的地址')"
              >
            </p>
            <p class="whole-item-tips">
              {{ $t('应用上线到蓝鲸应用市场的访问地址，你也可以在创建后修改选项') }}
            </p>
          </div>
        </div>
      </div>

      <div
        v-if="formLoading"
        class="form-loading"
      >
        <img src="/static/images/create-app-loading.svg">
        <p> {{ $t('应用创建中，请稍候') }} </p>
      </div>
      <div
        v-else
        class="form-actions"
        data-test-id="createDefault_btn_createApp"
      >
        <bk-button
          theme="primary"
          size="large"
          class="submit-mr"
          type="submit"
        >
          {{ $t('创建应用') }}
        </bk-button>
        <bk-button
          size="large"
          class="reset-ml ml15"
          @click.prevent="back"
        >
          {{ $t('返回') }}
        </bk-button>
      </div>
    </form>
  </div>
</template>
<script>
import _ from 'lodash';
import sidebarDiffMixin from '@/mixins/sidebar-diff-mixin';
export default {
  mixins: [sidebarDiffMixin],
  data() {
    return {
      formLoading: false,
      regionChoices: [],
      regionDescription: '',
      regionChoose: 'default',
      errorFields: [],
    };
  },
  computed: {
    platformFeature() {
      return this.$store.state.platformFeature;
    },
  },
  mounted() {
    this.form = $('#form-create-app').parsley();
    this.$form = this.form.$element;

    // Auto clearn ServerError message for field
    this.form.on('form:validated', (target) => {
      _.each(target.fields, (field) => {
        field.removeError('serverError');
      });
    });
    window.Parsley.on('field:error', function () {
      // 防止出现多条错误提示
      this.$element.parsley().removeError('serverError');
    });
  },
  created() {
    this.fetchSpecsByRegion();
  },
  methods: {
    // 格式化参数
    formatParams() {
      const formData = this.$form.serializeObject();
      const params = {
        region: this.regionChoose || formData.region,
        code: formData.code,
        name: formData.name,
        market_params: {
          source_tp_url: formData.source_tp_url,
        },
      };
      return params;
    },

    submitCreateForm() {
      if (!this.form.isValid()) {
        return;
      }
      const params = this.formatParams();

      this.$http.post(`${BACKEND_URL}/api/bkapps/third-party/`, params).then((resp) => {
        const objectKey = `SourceInitResult${Math.random().toString(36)}`;
        if (resp.source_init_result) {
          localStorage.setItem(objectKey, JSON.stringify(resp.source_init_result.extra_info));
        }
        const path = `/developer-center/apps/${resp.application.code}/create/success`;
        this.$router.push({
          path,
          query: { objectKey },
        });
      }, (resp) => {
        const body = resp;
        let fieldFocused = false;
        // Error message for individual fields
        if (body.fields_detail !== undefined) {
          _.forEach(body.fields_detail || [], (detail, key) => {
            if (key === 'non_field_errors') {
              this.globalErrorMessage = detail[0];
              window.scrollTo(0, 0);
            } else {
              const field = this.$form.find(`input[name="${key}"]`).parsley();
              if (field) {
                field.addError('serverError', { message: detail[0] });
                if (!fieldFocused) {
                  field.$element.focus();
                  fieldFocused = true;
                }
                this.errorFields.push(key);
              } else {
                this.globalErrorMessage = detail[0];
                window.scrollTo(0, 0);
              }
            }
          });
        } else {
          this.globalErrorMessage = body.detail;
          window.scrollTo(0, 0);
        }
      })
        .then(() => {
          this.formLoading = false;
        });
    },
    fetchSpecsByRegion() {
      this.$http.get(`${BACKEND_URL}/api/bkapps/regions/specs`).then((resp) => {
        this.allRegionsSpecs = resp;
        _.forEachRight(this.allRegionsSpecs, (value, key) => {
          this.regionChoices.push({
            key,
            value: value.display_name,
            description: value.description,
          });
        });
        this.regionChoose = this.regionChoices[0].key;
        this.regionDescription = this.allRegionsSpecs[this.regionChoose].description;
        // 收集初始依赖
        this.$nextTick(() => {
          const data = this.formatParams();
          this.initSidebarFormData(data);
        });
      });
    },
    async back() {
      // 内容变更输入弹窗提示
      const isSwitching = await this.handleBeforeFunction();
      if (!isSwitching) {
        return;
      }
      this.$router.push({
        name: 'myApplications',
      });
    },
    handleInput(key) {
      if (this.errorFields.length) {
        if (this.errorFields.includes(key)) {
          // 输入清除错误提示
          const field = this.$form.find(`input[name="${key}"]`).parsley();
          field.removeError('serverError', { updateClass: true });
          this.errorFields.splice(this.errorFields.indexOf(key), 1);
        }
      }
    },
    async handleBeforeFunction() {
      const data = this.formatParams();
      return this.$isSidebarClosed(JSON.stringify(data));
    },
  },
};
</script>
<style lang="scss" scoped>
    @import './default.scss';
</style>
