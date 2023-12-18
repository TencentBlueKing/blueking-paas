<template>
  <section class="config-item">
    <div class="title">
      {{ config.title }}
      <div class="edit-container" @click="handleEdit" v-if="!isEdit">
        <i class="paasng-icon paasng-edit-2 pl10" />
        {{ $t('编辑') }}
      </div>
    </div>
    <p class="tips">
      {{ config.tips }}
      <a
        v-if="config.url"
        :href="GLOBAL.DOC.SERVE_DISCOVERY"
        target="_blank"
      >
        {{ $t('使用指南') }}
      </a>
    </p>

    <div
      class="content"
      v-if="!isEdit"
    >
      <template v-if="config.list?.length">
        <div class="header">
          <div
            v-for="(col, index) in config.headerCol"
            :key="index"
            class="header-item"
            :class="`header-${index + 1}`"
          >
            {{ col }}
          </div>
        </div>
        <div
          class="body"
          v-if="dataName !== 'dnsServerData'"
        >
          <div
            v-for="(item, index) in config.list"
            :key="index"
            class="row"
            :class="`col-${index + 1}`"
          >
            <div class="col">{{ item.key }}</div>
            <div class="col" v-if="(typeof item.value === 'string')">{{ item.value || '--' }}</div>
            <div class="col" v-else>{{ item.value.join('; ') || '--' }}</div>
          </div>
        </div>
        <div
          class="body"
          v-else
        >
          <div
            v-for="(item, index) in config.list"
            :key="index"
            class="row"
            :class="`col-${index + 1}`"
          >
            <div class="col">{{ item }}</div>
          </div>
        </div>
      </template>

      <!-- 无数据状态 -->
      <bk-exception
        v-else
        class="exception-wrap-item exception-part"
        type="empty"
        scene="part"
      ></bk-exception>
    </div>

    <template v-else>
      <!-- 服务发现-编辑态 -->
      <div
        class="content"
        v-if="dataName === 'serviceFormData'"
      >
        <div class="body">
          <bk-form
            ref="serviceFormData"
            :label-width="200"
            :model="serviceFormData"
            ext-cls="form-config-cls"
            form-type="vertical"
          >
            <div
              v-for="(service, index) in serviceFormData.service"
              :class="{ 'hide-label': index > 0 }"
              class="form-item-wrapper"
              :key="index"
            >
              <bk-form-item
                style="width: 240px; margin-right: 16px"
                :label="$t('应用ID')"
                :required="true"
                :icon-offset="5"
                :rules="rules.id"
                :property="'service.' + index + '.id'"
              >
                <bk-input
                  v-model="service.id"
                  :placeholder="$t('请输入应用 ID')"
                ></bk-input>
              </bk-form-item>
              <!-- 非必填，默认为default -->
              <bk-form-item
                style="width: 240px"
                ext-cls="not-margin-top-cls"
                :label="$t('模块名称')"
                :icon-offset="5"
                :rules="rules.module"
                :property="'service.' + index + '.module'"
              >
                <bk-input
                  v-model="service.module"
                  :placeholder="$t('请输入模块名称，不填则默认为主模块')"
                ></bk-input>
              </bk-form-item>
              <!-- 第一个元素设置 -->
              <bk-form-item
                :key="index"
                ext-cls="icon-cls"
              >
                <i
                  class="icon paasng-icon paasng-plus-circle-shape mr10"
                  @click="addService('serviceFormData')"
                ></i>
                <i
                  class="paasng-icon paasng-minus-circle-shape"
                  @click="deleteService(index, 'serviceFormData')"
                ></i>
              </bk-form-item>
            </div>
          </bk-form>
        </div>
      </div>

      <!-- 域名解析-编辑态 -->
      <div
        class="content"
        v-if="dataName === 'dnsRuleFormData'"
      >
        <div class="body">
          <bk-form
            ref="dnsRuleFormData"
            :label-width="200"
            :model="dnsRuleFormData"
            ext-cls="form-config-cls"
            form-type="vertical"
          >
            <div
              v-for="(service, index) in dnsRuleFormData.service"
              :class="{ 'hide-label': index > 0 }"
              class="form-item-wrapper"
              :key="index"
            >
              <bk-form-item
                style="width: 240px; margin-right: 16px"
                label="IP"
                :required="true"
                :icon-offset="5"
                :rules="rules.ip"
                :property="'service.' + index + '.ip'"
              >
                <bk-input
                  v-model="service.ip"
                  :placeholder="$t('请输入 IP')"
                ></bk-input>
              </bk-form-item>
              <bk-form-item
                style="width: 240px"
                ext-cls="not-margin-top-cls"
                :label="$t('域名')"
                :required="true"
                :icon-offset="5"
                :rules="rules.hostnames"
                :property="'service.' + index + '.hostnames'"
              >
                <bk-tag-input
                  :placeholder="$t('请输入域名')"
                  v-model="service.hostnames"
                  :allow-create="true"
                  :allow-auto-match="true"
                  :has-delete-icon="true"
                ></bk-tag-input>
              </bk-form-item>
              <!-- 第一个元素设置 -->
              <bk-form-item
                :key="index"
                ext-cls="icon-cls"
              >
                <i
                  class="icon paasng-icon paasng-plus-circle-shape mr10"
                  @click="addService('dnsRuleFormData')"
                ></i>
                <i
                  class="paasng-icon paasng-minus-circle-shape"
                  @click="deleteService(index, 'dnsRuleFormData')"
                ></i>
              </bk-form-item>
            </div>
          </bk-form>
        </div>
      </div>

      <!-- DNS 服务器 -->
      <div
        class="content"
        v-if="dataName === 'dnsServerData'"
      >
        <div class="body">
          <bk-form
            ref="dnsServerData"
            :label-width="200"
            :model="dnsServerData"
            ext-cls="form-config-cls"
            form-type="vertical"
          >
            <div
              v-for="(service, index) in dnsServerData.service"
              :class="{ 'hide-label': index > 0 }"
              class="form-item-wrapper"
              :key="index"
            >
              <bk-form-item
                style="width: 240px"
                label="nameserver"
                :required="true"
                :icon-offset="5"
                :rules="rules.name"
                :property="'service.' + index + '.name'"
              >
                <bk-input
                  v-model="service.name"
                  :placeholder="$t('请输入')"
                ></bk-input>
              </bk-form-item>
              <bk-form-item
                :key="index"
                ext-cls="icon-cls"
              >
                <i
                  class="icon paasng-icon paasng-plus-circle-shape mr10"
                  @click="addService('dnsServerData')"
                ></i>
                <i
                  class="paasng-icon paasng-minus-circle-shape"
                  @click="deleteService(index, 'dnsServerData')"
                ></i>
              </bk-form-item>
            </div>
          </bk-form>
        </div>
      </div>
    </template>
    <div
      class="footer-btn-wrapper"
      v-if="isEdit"
    >
      <bk-button
        :theme="'primary'"
        class="mr10"
        @click="handleSave"
      >
        {{ $t('保存') }}
      </bk-button>
      <bk-button
        :theme="'default'"
        type="submit"
        @click="handleCancel"
      >
        {{ $t('取消') }}
      </bk-button>
    </div>
  </section>
</template>

<script>import appBaseMixin from '@/mixins/app-base-mixin.js';
import { cloneDeep } from 'lodash';
export default {
  mixins: [appBaseMixin],
  props: {
    data: {
      type: Array,
      default: () => [],
    },
    config: {
      type: Object,
      default: () => {},
    },
    dataName: {
      type: String,
      default: '',
    },
  },
  data() {
    return {
      isEdit: false,
      // 服务发现
      serviceFormData: {
        service: [{ id: '', module: '' }],
      },
      // 域名解析
      dnsRuleFormData: {
        service: [{ ip: '', hostnames: [] }],
      },
      // DNS 服务器
      dnsServerData: {
        service: [{ name: '' }],
      },
      // 备份数据
      dataBackup: {},
      rules: {
        // 应用ID
        id: [
          {
            required: true,
            message: this.$t('该字段是必填项'),
            trigger: 'blur',
          },
          {
            max: 16,
            message: this.$t('请输入 3-16 字符的小写字母、数字、连字符(-)，以小写字母开头'),
            trigger: 'blur',
          },
          {
            validator(val) {
              const reg = /^[a-z][a-z0-9-]*$/;
              return reg.test(val);
            },
            message: this.$t('格式不正确，只能包含：小写字母、数字、连字符(-)，首字母必须是字母'),
            trigger: 'blur',
          },
        ],
        module: [
          {
            validator(val) {
              // 允许不填
              if (val === '') {
                return true;
              }
              const reg = /^[a-z][a-z0-9-]{1,16}$/;
              return reg.test(val);
            },
            message: this.$t('由小写字母和数字以及连接符(-)组成，不能超过 16 个字符'),
            trigger: 'blur',
          },
        ],
        ip: [
          {
            required: true,
            message: this.$t('必填项'),
            trigger: 'blur',
          },
          {
            validator(val) {
              if (val) {
                return true;
              }
              return false;
            },
            message: this.$t('必填项'),
            trigger: 'blur',
          },
        ],
        hostnames: [
          {
            required: true,
            message: this.$t('必填项'),
            trigger: 'blur',
          },
          {
            validator(val) {
              if (val) {
                return true;
              }
              return false;
            },
            message: this.$t('必填项'),
            trigger: 'blur',
          },
        ],
        name: [
          {
            required: true,
            message: this.$t('必填项'),
            trigger: 'blur',
          },
          {
            validator(val) {
              if (val) {
                return true;
              }
              return false;
            },
            message: this.$t('必填项'),
            trigger: 'blur',
          },
        ],
      },
    };
  },
  watch: {
    data: {
      handler(value) {
        if (!value.length) {
          return;
        }
        this[this.dataName].service = [];

        switch (this.dataName) {
          case 'serviceFormData':
            value.forEach((v) => {
              this.serviceFormData.service.push({ id: v.bk_app_code, module: v.module_name });
            });
            // 备份当前数据
            this.dataBackup[this.dataName] = cloneDeep(this.serviceFormData);
            break;
          case 'dnsRuleFormData':
            value.forEach((v) => {
              this.dnsRuleFormData.service.push({ ip: v.ip, hostnames: v.hostnames });
            });
            this.dataBackup[this.dataName] = cloneDeep(this.dnsRuleFormData);
            break;
          default:
            value.forEach((v) => {
              this.dnsServerData.service.push({ name: v });
            });
            this.dataBackup[this.dataName] = cloneDeep(this.dnsServerData);
            break;
        }
      },
      immediate: true,
    },
  },
  methods: {
    // 对应数据尾部添加
    addService(dataName) {
      this[dataName].service.push({ id: '', module: '' });
    },

    // 删除对应数据下的指定项
    deleteService(index, dataName) {
      this[dataName].service.splice(index, 1);
    },

    // 编辑
    handleEdit() {
      this.isEdit = true;
    },

    // 取消
    handleCancel() {
      this.isEdit = false;

      if (this.dataBackup[this.dataName]) {
        // 数据重置
        this[this.dataName] = cloneDeep(this.dataBackup[this.dataName]);
      } else {
        this.initFormatData();
      }
    },

    // 无数据默认值
    initFormatData() {
      switch (this.dataName) {
        case 'serviceFormData':
          this.serviceFormData.service = [{ id: '', module: '' }];
          break;
        case 'dnsRuleFormData':
          this.dnsRuleFormData.service = [{ ip: '', hostnames: [] }];
          break;
        default:
          this.dnsServerData.service = [{ name: '' }];
          break;
      }
    },

    // 全量保存服务发现
    async saveServiceDiscoveryData() {
      const data = this.formatServiceData();

      try {
        await this.$store.dispatch('deploy/saveServiceDiscoveryData', {
          appCode: this.appCode,
          data,
        });
        this.$paasMessage({
          theme: 'success',
          message: this.$t('保存成功'),
        });
        this.$emit('refresh');
        // 更新服务发现
        this.isEdit = false;
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || this.$t('接口异常'),
        });
      }
    },

    // 保存
    handleSave() {
      // 空值保存
      if (!this[this.dataName].service.length) {
        this.saveExecution();
        return;
      }
      // 表单校验
      this.$refs[this.dataName].validate().then(() => {
        this.saveExecution();
      }, (validator) => {
        console.error(`${validator.field}：${validator.content}`);
      });
    },

    // 调用对用接口
    saveExecution() {
      // 备份数据更新
      this.dataBackup[this.dataName] = cloneDeep(this[this.dataName]);
      switch (this.dataName) {
        case 'serviceFormData':
          this.saveServiceDiscoveryData();
          break;
        case 'dnsRuleFormData':
          this.$emit('save', { key: 'host_aliases', value: this.formatdnsRuleData() });
          break;
        default:
          this.$emit('save', { key: 'nameservers', value: this.formatdnsServerData() });
          break;
      }
    },

    // 服务发现数据格式化
    formatServiceData() {
      const results = this.serviceFormData.service.map((item) => {
        const resultItem = {
          bk_app_code: item.id,
        };
        // 模块为费必填项
        if (item.module) {
          resultItem.module_name = item.module;
        }
        return resultItem;
      });
      return { bk_saas: results };
    },

    // 域名解析数据格式化
    formatdnsRuleData() {
      return this.dnsRuleFormData.service.map(item => ({
        ip: item.ip,
        hostnames: item.hostnames,
      }));
    },

    // DNS服务器数据格式化
    formatdnsServerData() {
      return this.dnsServerData.service.map(item => item.name);
    },
  },
};
</script>

<style lang="scss" scoped>
.config-item {
  position: relative;
  padding: 12px 24px 12px 0;
  background: #fff;

  .title {
    display: flex;
    font-weight: 700;
    font-size: 14px;
    color: #313238;
    line-height: 22px;
    .edit-container{
      color: #3A84FF;
      font-size: 12px;
      cursor: pointer;
      padding-left: 10px;
    }
  }

  .tips {
    font-size: 12px;
    color: #979ba5;
    line-height: 20px;
  }

  .content {
    margin-top: 14px;
    .header {
      display: flex;
      .header-item {
        width: 240px;
        font-size: 14px;
        color: #979ba5;
        line-height: 26px;
        &:first-child {
          margin-right: 16px;
          padding-left: 40px;
        }
      }
    }
    .body {
      .row {
        display: flex;

        .col {
          width: 240px;
          font-size: 14px;
          color: #313238;
          line-height: 26px;

          &:first-child {
            margin-right: 16px;
            padding-left: 40px;
          }
        }
      }
    }
  }

  .edit-btn {
    position: absolute;
    right: 24px;
    top: 12px;
  }

  .footer-btn-wrapper {
    margin-top: 24px;
  }
}

.form-config-cls {
  .hide-label {
    margin-top: 10px;

    /deep/ .bk-label {
      display: none;
    }
  }
}
.form-item-wrapper {
  display: flex;
  align-content: center;

  &:first-child .icon-cls {
    transform: translateY(34px);
  }
  .not-margin-top-cls {
    margin-top: 0 !important;
  }

  .icon-cls {
    margin-top: 0 !important;
    margin-left: 15px;

    i {
      color: #c4c6cc;
      cursor: pointer;
    }
  }
}
</style>
