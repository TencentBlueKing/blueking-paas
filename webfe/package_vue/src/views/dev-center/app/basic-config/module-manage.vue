<template lang="html">
  <div
    v-en-class="'en-label'"
    class="right-main"
  >
    <app-top-bar
      :title="$t('模块管理')"
      :can-create="canCreateModule"
      :cur-module="curAppModule"
      :module-list="curAppModuleList"
    />
    <paas-content-loader
      :is-loading="isLoading"
      placeholder="module-manage-loading"
      :offset-top="25"
      class="app-container middle module-container card-style"
    >
      <section>
        <div class="module-info-item mt15">
          <div class="title">
            {{ $t('基本信息') }}
          </div>
          <div class="info">
            {{ $t('模块的基本信息') }}
          </div>
          <div class="content no-border">
            <table class="ps-table ps-table-border mt20">
              <tr>
                <td
                  class="has-right-border"
                  style="width: 220px;"
                >
                  {{ $t('模块名称') }}
                </td>
                <td>{{ moduleName || '--' }}</td>
              </tr>
              <tr v-if="curAppInfo.application.is_plugin_app">
                <td
                  class="has-right-border"
                  style="width: 220px;"
                >
                  {{ $t('模块类型') }}
                </td>
                <td>
                  {{ $t('蓝鲸插件') }} <a
                    target="_blank"
                    :href="GLOBAL.LINK.BK_PLUGIN"
                    style="color: #3a84ff"
                  > {{ $t('查看详情') }} </a>
                </td>
              </tr>
              <tr v-if="curAppModule.web_config.templated_source_enabled">
                <td
                  class="has-right-border"
                  style="width: 220px;"
                >
                  {{ $t('初始化模板类型') }}
                </td>
                <td>{{ initTemplateTypeDisplay || '--' }}</td>
              </tr>
              <tr v-if="curAppModule.web_config.templated_source_enabled">
                <td
                  class="has-right-border"
                  style="width: 220px;"
                >
                  {{ $t('初始化模板说明') }}
                </td>
                <td>
                  {{ initTemplateDesc || '--' }}
                  <a
                    v-if="!curAppModule.repo.linked_to_internal_svn && initTemplateDesc"
                    class="ml5"
                    href="javascript: void(0);"
                    @click="handleDownloadTemplate"
                  > {{ $t('下载模板代码') }} </a>
                </td>
              </tr>
              <tr v-if="curAppModule.web_config.runtime_type !== 'custom_image'">
                <td
                  class="has-right-border"
                  style="width: 220px;"
                >
                  {{ $t('源码管理') }}
                </td>
                <td>
                  <template v-if="isSmartApp">
                    {{ $t('蓝鲸 S-mart 源码包') }}
                  </template>
                  <div v-else>
                    {{ curAppModule.source_origin === 1 || curAppModule.source_origin === GLOBAL.APP_TYPES.SCENE_APP ? $t('代码库') : $t('蓝鲸运维开发平台提供源码包') }}
                    <a
                      v-if="lessCodeFlag && curAppModule.source_origin === GLOBAL.APP_TYPES.LESSCODE_APP"
                      :href="lessCodeData.address_in_lesscode || 'javascript:;'"
                      :target="lessCodeData.address_in_lesscode ? '_blank' : ''"
                      class="ml5"
                      @click="handleLessCode"
                    >{{ $t('查看') }}</a>
                  </div>
                </td>
              </tr>
              <tr>
                <td
                  class="has-right-border"
                  style="width: 220px;"
                >
                  {{ $t('所属集群') }}
                </td>
                <td v-if="(curAppModule.clusters.stag.bcs_cluster_id === curAppModule.clusters.prod.bcs_cluster_id)">
                  <p>{{ curAppModule.clusters.prod.bcs_cluster_id }}</p>
                </td>
                <td v-else>
                  <p class="mb5">
                    {{ curAppModule.clusters.stag.bcs_cluster_id }}（{{ $t('预发布环境') }}）
                  </p>
                  <p>
                    {{ curAppModule.clusters.prod.bcs_cluster_id }}（{{ $t('生产环境') }}）
                  </p>
                </td>
              </tr>
            </table>
          </div>
        </div>
        <div class="module-info-item mt15">
          <div class="title">
            {{ $t('主模块设置') }}
          </div>
          <div class="info">
            {{ $t('每个应用拥有一个主模块，该模块地址将会被发布到蓝鲸市场等') }}
          </div>
          <div class="content no-border">
            <bk-button
              theme="primary"
              :disabled="hasBeenMainModule"
              :loading="setModuleLoading"
              @click="setMainModule"
            >
              {{ hasBeenMainModule ? $t('该模块已是主模块') : $t('设置该模块为主模块') }}
            </bk-button>
          </div>
        </div>

        <div
          v-if="curAppModule.source_origin === GLOBAL.APP_TYPES.NORMAL_APP || curAppModule.source_origin === GLOBAL.APP_TYPES.SCENE_APP"
          class="module-info-item mt15"
        >
          <div class="title">
            {{ $t('代码源') }}
          </div>
          <div class="info">
            {{ $t('修改模块绑定的源码仓库') }}
          </div>
          <div class="content no-border">
            <section class="code-depot">
              <div
                v-for="(item, index) in sourceControlTypes"
                :key="index"
                :class="['code-depot-item mr10', { 'on': item.value === selectedSourceControlType }, { 'disabled': sourceControlDisabled && item.value === 'bk_svn' }]"
                @click="changeSelectedSourceControl(item.value)"
              >
                <img :src="'/static/images/' + item.imgSrc + '.png'">
                <p
                  class="sourceControlTypeInfo"
                  :title="item.name"
                >
                  {{ item.name }}
                </p>
              </div>
            </section>

            <!-- Git 相关额外代码 start -->
            <template v-if="curSourceControl && curSourceControl.auth_method === 'oauth'">
              <git-extend
                :key="selectedSourceControlType"
                :git-control-type="selectedSourceControlType"
                :is-auth="gitExtendConfig[selectedSourceControlType].isAuth"
                :is-loading="gitExtendConfig[selectedSourceControlType].isLoading"
                :alert-text="gitExtendConfig[selectedSourceControlType].alertText"
                :auth-address="gitExtendConfig[selectedSourceControlType].authAddress"
                :auth-docs="gitExtendConfig[selectedSourceControlType].authDocs"
                :fetch-method="gitExtendConfig[selectedSourceControlType].fetchMethod"
                :repo-list="gitExtendConfig[selectedSourceControlType].repoList"
                :selected-repo-url.sync="gitExtendConfig[selectedSourceControlType].selectedRepoUrl"
                @change="handleSelectedRepoUrlChange"
              />
              <div class="form-group">
                <label class="form-label">
                  {{ $t('部署目录') }}
                  <i
                    v-bk-tooltips="sourceDirTip"
                    class="paasng-icon paasng-info-circle"
                  />
                </label>
                <div class="form-group-flex">
                  <p class="mt10">
                    <bk-input
                      v-model="sourceControlChangeForm.sourceDir"
                      class="source-dir"
                      :class="isSourceDirInvalid ? 'error' : ''"
                      :placeholder="$t('请输入应用所在子目录，并确保 app_desc.yaml 文件在该目录下，不填则默认为根目录')"
                    />
                    <ul
                      v-if="isSourceDirInvalid"
                      class="parsley-errors-list"
                    >
                      <li class="parsley-pattern">
                        {{ $t('支持子目录、如 ab/test，允许字母、数字、点(.)、下划线(_)、和连接符(-)，但不允许以点(.)开头') }}
                      </li>
                    </ul>
                  </p>
                </div>
              </div>
            </template>

            <!-- 用户自定义git、svn账号信息 start -->
            <repo-info
              v-if="curSourceControl && curSourceControl.auth_method === 'basic'"
              ref="repoInfo"
              :key="renderRepoInfoIndex"
              :type="selectedSourceControlType"
              :edited="isRepoInfoEdited"
              :default-url="curAppModule.repo.trunk_url"
              :default-account="curAppModule.repo_auth_info.username"
              :default-dir="curAppModule.repo.source_dir"
              @change="handleRepoInfoChange"
            />
            <!-- 用户自定义git、svn账号信息 end -->

            <!-- Git 相关额外代码 end -->
            <div class="switch-button">
              <template v-if="(curSourceControl && curSourceControl.auth_method === 'basic') && !isRepoInfoEdited">
                <bk-button
                  theme="primary"
                  @click="sureEditRepoInfo"
                >
                  {{ $t('编辑源码仓库') }}
                </bk-button>
              </template>
              <template v-else>
                <bk-button
                  theme="primary"
                  :disabled="displaySwitchDisabled || isSourceDirInvalid"
                  :loading="switchLoading"
                  @click="sureSwitch"
                >
                  {{ $t('切换源码仓库') }}
                </bk-button>
                <bk-button
                  v-if="displaySwitchCancel"
                  style="margin-left: 6px;"
                  :disabled="switchLoading"
                  @click="resetSourceType"
                >
                  {{ $t('取消') }}
                </bk-button>
              </template>
            </div>
          </div>
        </div>

        <div
          v-if="curAppModule.source_origin === GLOBAL.APP_TYPES.IMAGE"
          class="module-info-item mt15"
        >
          <div class="title">
            {{ $t('镜像管理') }}
          </div>
          <div class="info">
            {{ $t('修改模块绑定的镜像信息') }}
          </div>

          <bk-form
            ref="validate2"
            :model="mirrorData"
            :rules="mirrorRules"
            :label-width="80"
          >
            <bk-form-item
              :label="$t('镜像类型')"
              style="margin-top: 20px;"
            >
              <bk-radio-group v-model="mirrorData.type">
                <bk-radio value="public">
                  {{ $t('公开') }}
                </bk-radio>
                <bk-radio
                  value="private"
                  disabled
                >
                  {{ $t('私有') }}
                </bk-radio>
              </bk-radio-group>
            </bk-form-item>
            <bk-form-item
              :label="$t('镜像地址')"
              :required="true"
              :property="'url'"
              error-display-type="normal"
            >
              <bk-popover
                v-if="isText"
                :content="curAppModule.repo.repo_url"
                placement="bottom"
                class="urlText"
              >
                <p>{{ curAppModule.repo.repo_url }}</p>
              </bk-popover>
              <bk-input
                v-else
                v-model="mirrorData.url"
                style="width: 520px;"
                :placeholder="$t('请输入镜像地址,不包含版本(tag)信息')"
                size="large"
                clearable
              >
                <template
                  v-if="GLOBAL.CONFIG.MIRROR_PREFIX"
                  slot="prepend"
                >
                  <div class="group-text">
                    {{ GLOBAL.CONFIG.MIRROR_PREFIX }}
                  </div>
                </template>
              </bk-input>
            </bk-form-item>
          </bk-form>
          <div
            class="content no-border"
            style="margin-left: 80px;"
          >
            <bk-button
              v-if="isText"
              theme="primary"
              :loading="switchLoading"
              @click="editDockerUrl"
            >
              {{ $t('编辑镜像地址') }}
            </bk-button>
            <bk-button
              v-else
              theme="primary"
              class="mr10"
              :disabled="!mirrorData.url"
              :loading="switchLoading"
              @click="switchDocker"
            >
              {{ $t('切换镜像') }}
            </bk-button>
            <bk-button
              v-if="!isText"
              theme="default"
              @click="isText = true"
            >
              {{ $t('取消') }}
            </bk-button>
          </div>
        </div>

        <div class="module-info-item mt15">
          <div class="title">
            {{ $t('部署限制') }}
          </div>
          <div class="info">
            {{ $t('开启部署权限控制，仅管理员可部署、下架该模块。') }}
          </div>
          <div class="content no-border">
            <table class="ps-table ps-table-border mt20">
              <tr>
                <td
                  class="has-right-border"
                  style="width: 150px;"
                >
                  {{ $t('预发布坏境') }}
                </td>
                <td>
                  <div class="">
                    <bk-switcher
                      v-model="deployLimit.stag"
                      theme="primary"
                      :disabled="isLimitDisabled"
                      @change="stagHandleChange(...arguments, 'stag')"
                    />
                    <span class="switcher-content">{{ deployLimitText.stag[deployLimit.stag] }}</span>
                  </div>
                </td>
              </tr>
              <tr>
                <td
                  class="has-right-border"
                  style="width: 150px;"
                >
                  {{ $t('生产环境-label') }}
                </td>
                <td>
                  <div class="">
                    <bk-switcher
                      v-model="deployLimit.prod"
                      theme="primary"
                      :disabled="isLimitDisabled"
                      @change="prodHandleChange(...arguments, 'prod')"
                    />
                    <span class="switcher-content">{{ deployLimitText.prod[deployLimit.prod] }}</span>
                  </div>
                </td>
              </tr>
            </table>
          </div>
        </div>
        <div
          v-if="engineEnabled"
          class="module-info-item"
        >
          <div class="title">
            {{ $t('出口 IP 管理') }}
          </div>
          <div class="info">
            {{ $t('如果模块环境需要访问设置了 IP 白名单的外部服务，你可以在这里获取应用的出口 IP 列表，以完成外部服务授权。') }} <strong class="strong"> {{ $t('每次打开开关后，需重新部署方可生效。') }} </strong>
          </div>
          <div class="content no-border">
            <div class="pre-release-wrapper">
              <div class="header">
                <div class="header-title">
                  {{ $t('预发布环境') }}
                </div>
                <div class="switcher-wrapper">
                  <span
                    v-if="gatewayInfos.stag.created !== 'Invalid date' && gatewayInfos.stag.node_ip_addresses.length && !gatewayInfosStagLoading"
                    class="f12 date-tip"
                    @click="stopCapturing"
                  >{{ gatewayInfos.stag.created + $t('已获取') }}</span>
                  <bk-switcher
                    v-model="gatewayEnabled.stag"
                    :disabled="curStagDisabled"
                    @change="gatewayInfosHandler(...arguments, 'stag')"
                  />
                </div>
              </div>
              <div
                class="ip-content"
                contenteditable="false"
              >
                <div
                  v-if="gatewayInfos.stag.node_ip_addresses.length"
                  class="copy-wrapper"
                  :title="$t('复制')"
                  @click="handleCopyIp('stag')"
                >
                  <i class="paasng-icon paasng-general-copy" />
                </div>
                <template v-if="gatewayInfos.stag.node_ip_addresses.length">
                  <div
                    v-for="(nodeIp, nodeIpIndex) of gatewayInfos.stag.node_ip_addresses"
                    :key="nodeIpIndex"
                    class="ip-item"
                  >
                    {{ nodeIp.internal_ip_address }}
                  </div>
                </template>
                <template v-else>
                  <div class="no-ip">
                    <p> {{ $t('暂未获取出流量 IP 列表') }} </p>
                    <p> {{ $t('如有需要请联系管理员获取') }} </p>
                  </div>
                </template>
              </div>
            </div>
            <div class="production-wrapper has-left">
              <div class="header">
                <div class="header-title">
                  {{ $t('生产环境') }}
                </div>
                <div class="switcher-wrapper">
                  <span
                    v-if="gatewayInfos.prod.created !== 'Invalid date' && gatewayInfos.prod.node_ip_addresses.length && !gatewayInfosProdLoading"
                    class="f12 date-tip"
                    @click="stopCapturing"
                  >{{ gatewayInfos.prod.created + $t('已获取') }}</span>
                  <bk-switcher
                    v-model="gatewayEnabled.prod"
                    :disabled="curProdDisabled"
                    @change="gatewayInfosHandler(...arguments, 'prod')"
                  />
                </div>
              </div>
              <div
                class="ip-content"
                contenteditable="false"
              >
                <div
                  v-if="gatewayInfos.prod.node_ip_addresses.length"
                  class="copy-wrapper"
                  :title="$t('复制')"
                  @click="handleCopyIp('prod')"
                >
                  <i class="paasng-icon paasng-general-copy" />
                </div>
                <template v-if="gatewayInfos.prod.node_ip_addresses.length">
                  <div
                    v-for="(nodeIp, nodeIpIndex) of gatewayInfos.prod.node_ip_addresses"
                    :key="nodeIpIndex"
                    class="ip-item"
                  >
                    {{ nodeIp.internal_ip_address }}
                  </div>
                </template>
                <template v-else>
                  <div class="no-ip">
                    <p> {{ $t('暂未获取出流量 IP 列表') }} </p>
                    <p> {{ $t('如有需要请联系管理员获取') }} </p>
                  </div>
                </template>
              </div>
            </div>
            <div class="ip-tips">
              <i class="paasng-icon paasng-info-circle" />
              {{ $t('注意：重复获取列表可能会获得不一样的结果，请及时刷新外部服务白名单列表') }}
            </div>
          </div>
        </div>
        <div
          v-if="canDeleteModule"
          class="module-info-item"
        >
          <div class="title">
            {{ $t('删除模块') }}
          </div>
          <div class="info">
            {{ $t('模块被删除后，其所申请的所有增强服务资源也会被回收。请在删除前与应用其他成员沟通。') }}
          </div>
          <div class="content no-border">
            <bk-button
              theme="danger"
              @click="showRemovePrompt"
            >
              {{ $t('删除模块') }}
            </bk-button>
            <div class="ps-text-warn spacing-x1">
              {{ $t('该操作无法撤回') }}
            </div>
          </div>
        </div>
      </section>
    </paas-content-loader>

    <bk-dialog
      v-model="delAppDialog.visiable"
      width="540"
      :title="`${$t('确认删除模块')}【${curAppModule.name}】？`"
      :theme="'primary'"
      :mask-close="false"
      :loading="delAppDialog.isLoading"
      @after-leave="hookAfterClose"
    >
      <div class="ps-form">
        <div class="spacing-x1">
          {{ $t('请完整输入') }} <code>{{ curAppModule.name }}</code> {{ $t('来确认删除模块！') }}
        </div>
        <div class="ps-form-group">
          <input
            v-model="formRemoveConfirmCode"
            type="text"
            class="ps-form-control"
          >
        </div>
      </div>
      <div slot="footer">
        <bk-button
          theme="primary"
          :disabled="!formRemoveValidated"
          @click="submitRemoveModule"
        >
          {{ $t('确定') }}
        </bk-button>
        <bk-button
          theme="default"
          @click="delAppDialog.visiable = false"
        >
          {{ $t('取消') }}
        </bk-button>
      </div>
    </bk-dialog>

    <bk-dialog
      v-model="setMainModuleDialog.visiable"
      width="625"
      :title="`${$t('确定需要切换主模块为')}${curAppModule.name}？`"
      :header-position="'left'"
      :theme="'primary'"
      :mask-close="false"
      class="set-main-module-dialog"
    >
      <div>
        <p> {{ $t('切换后应用的短域名会指向到') }} {{ curAppModule.name }} {{ $t('模块：') }} </p>
        <p class="info-p">
          1、stag-dot-{{ $route.params.id }}.{{ getAppRootDomain(curAppModule.clusters.stag) }} : {{ $t('指向到应用') }} <span>{{ curAppModule.name }}</span> {{ $t('模块的预发布环境') }}
        </p>
        <p class="info-p">
          2、prod-dot-{{ $route.params.id }}.{{ getAppRootDomain(curAppModule.clusters.prod) }} ：{{ $t('指向到应用') }} <span>{{ curAppModule.name }}</span> {{ $t('模块的生产环境') }}
        </p>
        <p class="info-p">
          3、{{ $route.params.id }}.{{ getAppRootDomain(curAppModule.clusters.prod) }} ：{{ $t('指向到应用') }} <span>{{ curAppModule.name }}</span> {{ $t('模块的生产环境（应用市场和移动端默认使用该地址访问）') }}
        </p>
        <p class="info-p">
          {{ $t('请完全评估切换影响后，再进行主模块切换。') }}( <a
            class="a-link"
            target="_blank"
            :href="GLOBAL.DOC.MODULE_DEFAULT_INTRO"
          > {{ $t('文档：什么是主模块？') }} </a>)
        </p>
      </div>
      <div slot="footer">
        <bk-button
          theme="primary"
          @click="submitSetModule"
        >
          {{ $t('确定') }}
        </bk-button>
        <bk-button
          theme="default"
          @click="setMainModuleDialog.visiable = false"
        >
          {{ $t('取消') }}
        </bk-button>
      </div>
    </bk-dialog>

    <bk-dialog
      v-model="switchRepoDialog.visiable"
      width="540"
      :theme="'primary'"
      :mask-close="false"
      @after-close="afterRepoClose"
    >
      <div slot="header">
        <span
          v-bk-tooltips.top="`${$t('确认切换模块源码仓库为')} ${selectedSourceControlName}？`"
          class="top-middle"
        >
          {{ `${$t('确认切换模块源码仓库为')} ${selectedSourceControlName}？` }}
        </span>
      </div>
      <div>
        <p>{{ (curAppModule.repo.type === 'bk_svn' ? $t('该操作无法撤回，') : '') + $t('请确认已将当前源码与分支推送到新仓库中。') }}</p>
      </div>
      <div slot="footer">
        <bk-button
          theme="primary"
          @click="sureSwitchRepo"
        >
          {{ $t('确定') }}
        </bk-button>
        <bk-button
          theme="default"
          @click="switchRepoDialog.visiable = false"
        >
          {{ $t('取消') }}
        </bk-button>
      </div>
    </bk-dialog>

    <bk-dialog
      v-model="switchDockerDialog.visiable"
      width="540"
      :title="`${$t('确认切换镜像')}`"
      :theme="'primary'"
      :mask-close="false"
    >
      <div>
        <p> {{ $t('请确认已将镜像推送到新的镜像地址') }} </p>
      </div>
      <div slot="footer">
        <bk-button
          theme="primary"
          @click="sureSwitchRepo"
        >
          {{ $t('确定') }}
        </bk-button>
        <bk-button
          theme="default"
          @click="switchDockerDialog.visiable = false"
        >
          {{ $t('取消') }}
        </bk-button>
      </div>
    </bk-dialog>
  </div>
</template>

<script>import moment from 'moment';
import { DEFAULT_APP_SOURCE_CONTROL_TYPES } from '@/common/constants';
import gitExtend from '@/components/ui/git-extend';
import repoInfo from '@/components/ui/repo-info.vue';
import appTopBar from '@/components/paas-app-bar';
import appBaseMixin from '@/mixins/app-base-mixin';
import { fileDownload } from '@/common/utils';

export default {
  components: {
    gitExtend,
    repoInfo,
    appTopBar,
  },
  mixins: [appBaseMixin],
  props: {
    appInfo: {
      type: Object,
    },
  },
  data() {
    return {
      isLoading: false,
      formRemoveConfirmCode: '',
      isRepoInfoEdited: false,
      curEnv: '',
      gatewayEnabled: {
        stag: false,
        prod: false,
      },
      gatewayInfos: {
        stag: {
          created: '',
          node_ip_addresses: [],
        },
        prod: {
          created: '',
          node_ip_addresses: [],
        },
      },
      renderRepoInfoIndex: 0,
      delAppDialog: {
        visiable: false,
        isLoading: false,
      },
      gatewayInfosStagLoading: false,
      gatewayInfosProdLoading: false,
      isGatewayInfosBeClearing: false,

      sourceControlTypes: DEFAULT_APP_SOURCE_CONTROL_TYPES,
      sourceControlType: '',
      gitExtendConfig: {
        // 蓝鲸 gitlab
        bk_gitlab: {
          isAuth: true,
          isLoading: false,
          alertText: '',
          authAddress: undefined,
          fetchMethod: this.generateFetchRepoListMethod('bk_gitlab'),
          repoList: [],
          selectedRepoUrl: '',
          sourceDir: '',
          authDocs: '',
        },
        // 工蜂
        tc_git: {
          isAuth: true,
          isLoading: false,
          alertText: '',
          authAddress: undefined,
          fetchMethod: this.generateFetchRepoListMethod('tc_git'),
          repoList: [],
          selectedRepoUrl: '',
          sourceDir: '',
          authDocs: '',
        },
        // github
        github: {
          isAuth: true,
          isLoading: false,
          alertText: '',
          authAddress: undefined,
          fetchMethod: this.generateFetchRepoListMethod('github'),
          repoList: [],
          selectedRepoUrl: '',
          sourceDir: '',
          authDocs: '',
        },
        // gitee
        gitee: {
          isAuth: true,
          isLoading: false,
          alertText: '',
          authAddress: undefined,
          fetchMethod: this.generateFetchRepoListMethod('gitee'),
          repoList: [],
          selectedRepoUrl: '',
          sourceDir: '',
          authDocs: '',
        },
        // SVN 代码库
        bare_svn: {
          isAuth: true,
          isLoading: false,
          alertText: '',
          authAddress: undefined,
          selectedRepoUrl: '',
          authInfo: {
            account: '',
            password: '',
          },
          sourceDir: '',
        },
        // Git 代码库
        bare_git: {
          isAuth: true,
          isLoading: false,
          alertText: '',
          authAddress: undefined,
          selectedRepoUrl: '',
          authInfo: {
            account: '',
            password: '',
          },
          sourceDir: '',
        },
      },

      initTemplateType: '',

      moduleName: '',

      switchLoading: false,

      setModuleLoading: false,

      hasBeenMainModule: false,
      setMainModuleDialog: {
        visiable: false,
      },

      switchRepoDialog: {
        visiable: false,
      },
      switchDockerDialog: {
        visiable: false,
      },
      selectedSourceControlName: '',
      selectedSourceControlType: '',

      initTemplateDesc: '',

      initLanguage: '',

      deployLimit: {
        stag: false,
        prod: false,
      },
      deployLimitText: {
        stag: { true: this.$t('开启部署权限控制，仅管理员可以部署、下架预发布环境'), false: this.$t('未开启部署权限控制，管理员、开发者都可以部署、下架预发布环境') },
        prod: { true: this.$t('开启部署权限控制，仅管理员可以部署、下架生产环境'), false: this.$t('未开启部署权限控制，管理员、开发者都可以部署、下架生产环境') },
      },
      sourceControlChangeForm: {
        sourceRepoUrl: '',
        sourceDir: '',
      },
      appModuleDomainInfo: {},
      sourceDirTip: {
        theme: 'light',
        allowHtml: true,
        content: this.$t('提示信息'),
        html: `<a target="_blank" href="${this.GLOBAL.DOC.DEPLOY_DIR}" style="color: #3a84ff">${this.$t('如何设置部署目录')}</a>`,
        placements: ['right'],
      },
      mirrorData: {
        type: 'public',
        url: '',
      },
      mirrorRules: {
        url: [
          {
            required: true,
            message: this.$t('该字段是必填项'),
            trigger: 'blur',
          },
          {
            validator(val) {
              return !val.includes(':');
            },
            message: this.$t('镜像地址中不能包含版本(tag)信息'),
            trigger: 'blur',
          },
        ],
      },
      sourceOrigin: this.GLOBAL.APP_TYPES.NORMAL_APP,
      isText: true,
      lessCodeData: {},
      lessCodeFlag: true,
    };
  },
  computed: {
    canDeleteModule() {
      return !this.curAppModule.is_default;
    },
    formRemoveValidated() {
      return this.curAppModule.name === this.formRemoveConfirmCode;
    },
    sourceControlDisabled() {
      return this.curAppModule.repo && this.curAppModule.repo.type !== 'bk_svn';
    },
    engineEnabled() {
      if (this.appInfo.config_info) {
        return this.appInfo.config_info.engine_enabled;
      }
      return false;
    },
    initTemplateTypeDisplay() {
      return `${this.initTemplateType}(${this.initLanguage})`;
    },
    isLimitDisabled() {
      return this.appInfo.role !== 'administrator';
    },
    curSourceControl() {
      const match = this.sourceControlTypes.find(item => item.value === this.selectedSourceControlType);
      return match;
    },
    isSourceDirInvalid() {
      if (this.sourceControlChangeForm.sourceDir === '') {
        return false;
      }
      return !/^((?!\.)[a-zA-Z0-9_./-]+|\s*)$/.test(this.sourceControlChangeForm.sourceDir);
    },
    displaySwitchDisabled() {
      const match = this.gitExtendConfig[this.selectedSourceControlType];

      if (match && !match.authInfo) {
        return this.curAppModule.repo.trunk_url === this.sourceControlChangeForm.sourceRepoUrl && this.curAppModule.repo.source_dir === this.sourceControlChangeForm.sourceDir;
      }

      if (match && match.authInfo) {
        return !this.sourceControlChangeForm.sourceRepoUrl || !match.authInfo.account
                        || !match.authInfo.password || !/^((?!\.)[a-zA-Z0-9_./-]+|\s*)$/.test(match.sourceDir);
      }

      return true;
    },
    displaySwitchCancel() {
      if (this.selectedSourceControlType !== this.curAppModule.repo.type) {
        return true;
      }
      return !this.displaySwitchDisabled;
    },
    curStagDisabled() {
      if (this.gatewayInfosStagLoading || this.isGatewayInfosBeClearing) {
        // 防抖, 不允许频繁切换
        return true;
      }
      if (this.gatewayInfos.stag.node_ip_addresses.length) {
        // 总是允许关闭出口 IP
        return false;
      }
      // 如果应用未支持开关出口IP管理, 则不允许打开出口IP
      return !this.curAppInfo.feature.TOGGLE_EGRESS_BINDING;
    },
    curProdDisabled() {
      if (this.gatewayInfosProdLoading || this.isGatewayInfosBeClearing) {
        // 防抖, 不允许频繁切换
        return true;
      }
      if (this.gatewayInfos.prod.node_ip_addresses.length) {
        // 总是允许关闭出口 IP
        return false;
      }
      // 如果应用未支持开关出口IP管理, 则不允许打开出口IP
      return !this.curAppInfo.feature.TOGGLE_EGRESS_BINDING;
    },
    entranceConfig() {
      return this.$store.state.region.entrance_config;
    },
    curUserFeature() {
      return this.$store.state.userFeature;
    },
    localLanguage() {
      return this.$store.state.localLanguage;
    },
  },
  watch: {
    appInfo() {
      // 云原生应用无需请求模块接口
      if (!this.isCloudNativeApp) {
        this.init();
      }
    },
    '$route'() {
      this.resetParams();
      if (!this.isCloudNativeApp) {
        this.init();
      }
    },
    'curAppModule.name'() {
      this.getLessCode();
    },
    'curAppModule.repo'(repo) {
      if (!repo) {
        this.curAppModule.repo = {};
      }
    },
  },
  created() {
    moment.locale(this.localLanguage);
  },
  mounted() {
    this.init();
  },
  methods: {
    async init() {
      this.isGatewayInfosBeClearing = false;

      if (!this.curAppInfo.web_config.engine_enabled) {
        return;
      }

      this.formRemoveConfirmCode = '';
      this.isLoading = true;

      if (this.appInfo.config_info && this.appInfo.config_info.engine_enabled) {
        this.getGatewayInfos('stag');
        this.getGatewayInfos('prod');
      }
      if (this.curAppModule.source_origin === 1 || this.curAppModule.source_origin === this.GLOBAL.APP_TYPES.SCENE_APP) {
        await this.fetchSourceControlTypes();
      }
      const sourceControlTypes = this.sourceControlTypes.map(e => e.value);
      for (const key in this.gitExtendConfig) {
        // 初始化 repo List
        const config = this.gitExtendConfig[key];
        sourceControlTypes.includes(key) && config.fetchMethod && config.fetchMethod();
      }
      this.getLessCode();
      // this.getModuleDomainInfo()
      await this.fetchEnvProtection();
      await this.fetchModuleInfo();
      await this.fetchLanguageInfo();
    },

    async getModuleDomainInfo() {
      try {
        const res = await this.$store.dispatch('module/getModuleDomainInfo', {
          appCode: this.$route.params.id || this.curAppCode,
        });
        this.appModuleDomainInfo = res;
      } catch (res) {
        this.$paasMessage({
          limit: 1,
          theme: 'error',
          message: res.detail || res.message || this.$t('接口异常'),
        });
      }
    },

    async fetchSourceControlTypes() {
      try {
        const res = await this.$store.dispatch('module/getModuleCodeTypes', {
          appCode: this.$route.params.id || this.curAppCode,
          moduleId: this.$route.params.moduleId || this.curModuleId,
        });
        this.sourceControlTypes.splice(0, this.sourceControlTypes.length, ...(res.results || []));
        this.sourceControlTypes = this.sourceControlTypes.map((e) => {
          e.imgSrc = e.value;
          if (e.value === 'bare_svn') {
            e.imgSrc = 'bk_svn';
          }
          return e;
        });
      } catch (res) {
        this.$paasMessage({
          limit: 1,
          theme: 'error',
          message: res.detail || res.message || this.$t('接口异常'),
        });
      }
    },

    handleCopyIp(env) {
      const copyIp = this.gatewayInfos[env].node_ip_addresses.map(item => item.internal_ip_address).join(';');
      const el = document.createElement('textarea');
      el.value = copyIp;
      el.setAttribute('readonly', '');
      el.style.position = 'absolute';
      el.style.left = '-9999px';
      document.body.appendChild(el);
      const selected = document.getSelection().rangeCount > 0 ? document.getSelection().getRangeAt(0) : false;
      el.select();
      document.execCommand('copy');
      document.body.removeChild(el);
      if (selected) {
        document.getSelection().removeAllRanges();
        document.getSelection().addRange(selected);
      }
      this.$bkMessage({ theme: 'primary', message: this.$t('复制成功'), delay: 2000, dismissable: false });
    },

    resetSourceType() {
      if (this.curAppModule.source_origin === 1 || this.curAppModule.source_origin === this.GLOBAL.APP_TYPES.SCENE_APP) {
        this.selectedSourceControlType = this.curAppModule.repo.type;
        this.sourceControlChangeForm.sourceRepoUrl = this.curAppModule.repo.trunk_url;
        this.sourceControlChangeForm.sourceDir = this.curAppModule.repo.source_dir;

        if (this.curAppModule.repo.type !== 'bk_svn') {
          const match = this.gitExtendConfig[this.selectedSourceControlType];
          match.selectedRepoUrl = this.curAppModule.repo.trunk_url || '';
          match.sourceDir = this.curAppModule.repo.source_dir || '';
          if (match.authInfo) {
            match.authInfo.account = this.curAppModule.repo_auth_info.username;
            match.authInfo.password = '';
          }
        }
      }
      this.isRepoInfoEdited = false;
    },
    async submitSetModule() {
      this.setMainModuleDialog.visiable = false;
      this.setModuleLoading = true;
      try {
        await this.$store.dispatch('module/setMainModule', {
          appCode: this.appInfo.code,
          modelName: this.curAppModule.name,
        });
        this.$paasMessage({
          theme: 'success',
          message: this.$t('主模块设置成功'),
        });
        this.hasBeenMainModule = true;
        this.$store.commit('updateCurAppModuleIsDefault', this.curAppModule.id);
      } catch (res) {
        this.$paasMessage({
          limit: 1,
          theme: 'error',
          message: res.detail || res.message || this.$t('接口异常'),
        });
      } finally {
        this.setModuleLoading = false;
      }
    },

    stagHandleChange(value, env) {
      this.fetchSetDeployLimit(env);
    },

    prodHandleChange(value, env) {
      this.fetchSetDeployLimit(env);
    },

    async fetchEnvProtection() {
      try {
        const res = await this.$store.dispatch('module/getEnvProtection', {
          appCode: this.appInfo.code,
          modelName: this.curAppModule.name,
        });
        if (res.length) {
          if (res.length === 2) {
            res.forEach((item) => {
              this.deployLimit[item.environment] = true;
            });
          } else {
            const curEnv = res[0].environment;
            if (curEnv === 'stag') {
              this.deployLimit.stag = true;
              this.deployLimit.prod = false;
            } else {
              this.deployLimit.stag = false;
              this.deployLimit.prod = true;
            }
          }
        } else {
          this.deployLimit = {
            stag: false,
            prod: false,
          };
        }
      } catch (res) {
        this.$paasMessage({
          limit: 1,
          theme: 'error',
          message: res.detail || res.message || this.$t('接口异常'),
        });
      }
    },

    async fetchSetDeployLimit(env) {
      try {
        await this.$store.dispatch('module/setDeployLimit', {
          appCode: this.appInfo.code,
          modelName: this.curAppModule.name,
          params: {
            operation: 'deploy',
            env,
          },
        });
      } catch (res) {
        this.deployLimit[env] = !this.deployLimit[env];
        this.$paasMessage({
          limit: 1,
          theme: 'error',
          message: res.detail || res.message || this.$t('接口异常'),
        });
      }
    },

    async sureSwitchRepo() {
      if (this.switchLoading) {
        return false;
      }
      this.switchRepoDialog.visiable = false;
      this.switchDockerDialog.visiable = false;
      const config = this.gitExtendConfig[this.selectedSourceControlType];

      try {
        this.switchLoading = true;
        const params = {
          appCode: this.appInfo.code,
          modelName: this.curAppModule.name,
          data: {
            source_control_type: this.selectedSourceControlType,
            source_repo_url: this.sourceControlChangeForm.sourceRepoUrl,
            source_dir: this.sourceControlChangeForm.sourceDir,
          },
        };

        if (config && config.authInfo) {
          params.data.source_repo_auth_info = {
            username: config.authInfo.account,
            password: config.authInfo.password,
          };
        }

        if (this.curAppModule.source_origin === this.GLOBAL.APP_TYPES.IMAGE) {
          params.data.source_control_type = 'tc_docker';
          params.data.source_repo_url = `${this.GLOBAL.CONFIG.MIRROR_PREFIX}${this.mirrorData.url}`;
          params.data.source_repo_auth_info = {
            username: '',
            password: '',
          };
        }

        const res = await this.$store.dispatch('module/switchRepo', params);
        if (res.repo_type === 'tc_docker') {
          this.$paasMessage({
            theme: 'success',
            message: res.message,
          });
          this.isText = true;
        } else {
          if (this.selectedSourceControlType === 'bk_svn') {
            ['bare_git', 'tc_git'].forEach((item) => {
              this.gitExtendConfig[item].selectedRepoUrl = '';
            });
          } else {
            if (this.selectedSourceControlType === 'bk_gitlab') {
              this.gitExtendConfig.tc_git.selectedRepoUrl = '';
            } else {
              this.gitExtendConfig.bk_gitlab.selectedRepoUrl = '';
            }
          }
          this.$paasMessage({
            theme: 'success',
            message: this.$t('修改源码信息成功'),
          });
        }
        await this.fetchModuleInfo();
      } catch (res) {
        console.error(res);
        this.$paasMessage({
          limit: 1,
          theme: 'error',
          message: res.detail || res.message || this.$t('接口异常'),
        });
      } finally {
        this.switchLoading = false;
      }
    },

    resetParams() {
      this.gitExtendConfig = {
        bk_gitlab: {
          isAuth: true,
          isLoading: false,
          alertText: '',
          authAddress: undefined,
          fetchMethod: this.generateFetchRepoListMethod('bk_gitlab'),
          repoList: [],
          selectedRepoUrl: '',
          sourceDir: '',
        },
        tc_git: {
          isAuth: true,
          isLoading: false,
          alertText: '',
          authAddress: undefined,
          fetchMethod: this.generateFetchRepoListMethod('tc_git'),
          repoList: [],
          selectedRepoUrl: '',
          sourceDir: '',
        },
        github: {
          isAuth: true,
          isLoading: false,
          alertText: '',
          authAddress: undefined,
          fetchMethod: this.generateFetchRepoListMethod('github'),
          repoList: [],
          selectedRepoUrl: '',
          sourceDir: '',
        },
        gitee: {
          isAuth: true,
          isLoading: false,
          alertText: '',
          authAddress: undefined,
          fetchMethod: this.generateFetchRepoListMethod('gitee'),
          repoList: [],
          selectedRepoUrl: '',
          sourceDir: '',
        },
        bare_svn: {
          isAuth: true,
          isLoading: false,
          alertText: '',
          authAddress: undefined,
          selectedRepoUrl: '',
          authInfo: {
            account: '',
            password: '',
          },
          sourceDir: '',
        },
        bare_git: {
          isAuth: true,
          isLoading: false,
          alertText: '',
          authAddress: undefined,
          selectedRepoUrl: '',
          authInfo: {
            account: '',
            password: '',
          },
          sourceDir: '',
        },
      };
    },

    async fetchLanguageInfo() {
      try {
        const res = await this.$store.dispatch('module/getLanguageInfo');
        const { region } = this.curAppModule;

        const languages = res[region]?.languages?.[this.initLanguage] || [];
        const lanObj = languages.find(item => item.display_name === this.initTemplateType);
        this.initTemplateDesc = lanObj?.description || '';
      } catch (res) {
        this.$paasMessage({
          limit: 1,
          theme: 'error',
          message: res.detail || res.message || this.$t('接口异常'),
        });
      } finally {
        this.isLoading = false;
      }
    },

    async fetchModuleInfo() {
      try {
        await this.$store.dispatch('getAppInfo', {
          appCode: this.appInfo.code,
          moduleId: this.curAppModule.name,
        });
        this.hasBeenMainModule = this.curAppModule.is_default;
        this.moduleName = this.curAppModule.name;
        this.initLanguage = this.curAppModule.language;
        this.initTemplateType = this.curAppModule.template_display_name;
        this.renderRepoInfoIndex++;

        if (this.curAppModule.source_origin === 1 || this.curAppModule.source_origin === this.GLOBAL.APP_TYPES.SCENE_APP) {
          this.selectedSourceControlType = this.curAppModule.repo.type;
          this.sourceControlChangeForm.sourceRepoUrl = this.curAppModule.repo.trunk_url;
          this.sourceControlChangeForm.sourceDir = this.curAppModule.repo.source_dir;
          if (this.curAppModule.repo.type !== 'bk_svn' && this.gitExtendConfig[this.curAppModule.repo.type]) {
            this.gitExtendConfig[this.curAppModule.repo.type].selectedRepoUrl = this.curAppModule.repo.trunk_url;
            this.gitExtendConfig[this.curAppModule.repo.type].sourceDir = this.curAppModule.repo.source_dir || '';
          }
          if (['bare_svn', 'bare_git'].includes(this.curAppModule.repo.type)) {
            this.gitExtendConfig[this.curAppModule.repo.type].authInfo.account = this.curAppModule.repo_auth_info.username;
            this.gitExtendConfig[this.curAppModule.repo.type].authInfo.password = '';
            this.gitExtendConfig[this.curAppModule.repo.type].sourceDir = this.curAppModule.repo.source_dir || '';
          }
        }
      } catch (res) {
        this.$paasMessage({
          limit: 1,
          theme: 'error',
          message: res.detail || res.message || this.$t('接口异常'),
        });
      } finally {
        this.isRepoInfoEdited = false;
      }
    },

    sureEditRepoInfo() {
      this.isRepoInfoEdited = true;
    },

    sureSwitch() {
      this.selectedSourceControlName = this.sourceControlTypes.find(item => item.value === this.selectedSourceControlType).name;
      const config = this.gitExtendConfig[this.selectedSourceControlType];
      let sourceRepoUrl = config.selectedRepoUrl;
      switch (this.selectedSourceControlType) {
        case 'bk_gitlab':
        case 'github':
        case 'gitee':
        case 'tc_git':
          if (!sourceRepoUrl) {
            this.$paasMessage({
              theme: 'error',
              message: config.isAuth ? this.$t('请选择关联的远程仓库') : this.$t('请关联 git 账号'),
            });
            return;
          }
          break;
        case 'bare_svn':
        case 'bare_git':
          const repoData = this.$refs.repoInfo.getData();
          if (!repoData.url) {
            this.$paasMessage({
              theme: 'error',
              message: this.$t('请输入源代码地址'),
            });
            return;
          }
          if (!repoData.account) {
            this.$paasMessage({
              theme: 'error',
              message: this.$t('请输入账号'),
            });
            return;
          }
          if (!repoData.password) {
            this.$paasMessage({
              theme: 'error',
              message: this.$t('请输入密码'),
            });
            return;
          }

          break;
        case 'bk_svn':
        default:
          sourceRepoUrl = undefined;
          break;
      }
      this.switchRepoDialog.visiable = true;
    },
    afterRepoClose() {
      this.selectedSourceControlName = '';
    },
    generateFetchRepoListMethod(sourceControlType) {
      // 根据不同的 sourceControlType 生成对应的 fetchRepoList 方法
      return async () => {
        const config = this.gitExtendConfig[sourceControlType];
        try {
          config.isLoading = true;
          const resp = await this.$store.dispatch('getRepoList', { sourceControlType });
          config.repoList = resp.results.map((repo, index) => ({ name: repo.fullname, id: repo.http_url_to_repo }));
          config.isAuth = true;
        } catch (e) {
          const resp = e.response;
          config.isAuth = false;
          if (resp.status === 403 && resp.data.result) {
            config.authAddress = resp.data.address;
            config.authDocs = resp.data.auth_docs;
          }
        } finally {
          config.isLoading = false;
        }
      };
    },

    setMainModule() {
      this.setMainModuleDialog.visiable = true;
    },

    stopCapturing(event) {
      event.stopPropagation();
    },

    showRemovePrompt() {
      this.delAppDialog.visiable = true;
    },

    hookAfterClose() {
      this.formRemoveConfirmCode = '';
    },

    async submitRemoveModule() {
      try {
        await this.$store.dispatch('module/deleteModule', {
          appCode: this.appInfo.code,
          moduleName: this.curAppModule.name,
        });
        this.delAppDialog.visiable = false;
        this.$paasMessage({
          theme: 'success',
          message: this.$t('模块删除成功'),
        });
        this.$router.push({
          name: 'appSummary',
          params: {
            id: this.appInfo.code,
            moduleId: this.curAppModuleList.find(item => item.is_default).name,
          },
        });
        this.$store.dispatch('getAppInfo', { appCode: this.appInfo.code, moduleId: this.curAppModule.name });
      } catch (res) {
        console.warn(res);
        this.$paasMessage({
          limit: 1,
          theme: 'error',
          message: res.detail || res.message || this.$t('接口异常'),
        });
        this.delAppDialog.visiable = false;
      }
    },

    gatewayInfosHandler(payload, env) {
      this.curEnv = env;
      if (!payload) {
        const title = this.curEnv === 'stag' ? this.$t('确认清除预发布环境出口 IP 信息？') : this.$t('确认清除生产环境出口 IP 信息？');

        const _self = this;
        _self.$bkInfo({
          title,
          subTitle: this.$t('IP 列表可能会在下次重新获取时更新，届时请及时刷新外部服务白名单。'),
          maskClose: true,
          width: 420,
          extCls: 'paas-module-manager-switch-cls',
          confirmFn() {
            const appCode = _self.$route.params.id;
            const env = _self.curEnv;
            _self.isGatewayInfosBeClearing = true;
            _self.$store.dispatch('baseInfo/clearGatewayInfos', {
              appCode,
              env,
              moduleName: _self.curAppModule.name,
            }).then((res) => {
              _self.gatewayInfos[env] = {
                created: '',
                node_ip_addresses: [],
              };
              _self.gatewayEnabled[env] = false;
            })
              .catch((res) => {
                _self.$paasMessage({
                  limit: 1,
                  theme: 'error',
                  message: res.detail || this.$t('服务暂不可用，请稍后再试'),
                });
              })
              .finally((res) => {
                _self.isGatewayInfosBeClearing = false;
              });
          },
          cancelFn() {
            if (_self.curEnv === 'stag') {
              _self.gatewayEnabled.stag = true;
            } else {
              _self.gatewayEnabled.prod = true;
            }
          },
        });
      } else {
        this.enableGatewayInfos();
      }
    },

    getGatewayInfos(env) {
      const appCode = this.$route.params.id;
      this.$store.dispatch('baseInfo/getGatewayInfos', {
        appCode,
        env,
        moduleName: this.curAppModule.name,
      }).then((res) => {
        this.gatewayInfos[env] = {
          created: moment(res.rcs_binding_data.created).startOf('minute')
            .fromNow(),
          node_ip_addresses: res.rcs_binding_data.state.node_ip_addresses,
        };
        this.gatewayEnabled[env] = true;
      })
        .catch((res) => {
          this.gatewayInfos[env] = {
            created: '',
            node_ip_addresses: [],
          };
          this.gatewayEnabled[env] = false;
        });
    },

    enableGatewayInfos() {
      const appCode = this.$route.params.id;
      const env = this.curEnv;

      if (env === 'stag') {
        this.gatewayInfosStagLoading = true;
      } else {
        this.gatewayInfosProdLoading = true;
      }

      this.$store.dispatch('baseInfo/enableGatewayInfos', {
        appCode,
        env,
        moduleName: this.curAppModule.name,
      }).then((res) => {
        this.gatewayInfos[env] = {
          created: moment(res.rcs_binding_data.created).startOf('minute')
            .fromNow(),
          node_ip_addresses: res.rcs_binding_data.state.node_ip_addresses,
        };
        this.gatewayEnabled[env] = true;
      })
        .catch((res) => {
          if (env === 'stag') {
            this.gatewayEnabled.stag = false;
          } else {
            this.gatewayEnabled.prod = false;
          }
          this.$paasMessage({
            limit: 1,
            theme: 'error',
            message: res.detail || this.$t('服务暂不可用，请稍后再试'),
          });
        })
        .finally(() => {
          if (env === 'stag') {
            this.gatewayInfosStagLoading = false;
          } else {
            this.gatewayInfosProdLoading = false;
          }
        });
    },

    async handleDownloadTemplate() {
      try {
        const res = await this.$store.dispatch('getAppInitTemplateUrl', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
        });
        fileDownload(res.downloadable_address);
      } catch (e) {
        this.$paasMessage({
          limit: 1,
          theme: 'error',
          message: resp.detail || this.$t('服务暂不可用，请稍后再试'),
        });
      }
    },
    changeSelectedSourceControl(sourceControlType) {
      // bk svn禁止切换
      if (sourceControlType === 'bk_svn' && this.sourceControlDisabled) {
        return;
      }

      this.selectedSourceControlType = sourceControlType;
      const config = this.gitExtendConfig[this.selectedSourceControlType];
      this.isRepoInfoEdited = ['bare_svn', 'bare_git'].includes(sourceControlType) && sourceControlType !== this.curAppModule.repo.type;
      this.renderRepoInfoIndex++;
      if (sourceControlType === this.curAppModule.repo.type) {
        if (config) {
          config.selectedRepoUrl = this.curAppModule.repo.trunk_url;
        }
        this.sourceControlChangeForm.sourceRepoUrl = this.curAppModule.repo.trunk_url;
        this.sourceControlChangeForm.sourceDir = this.curAppModule.repo.source_dir;
      } else {
        this.sourceControlChangeForm.sourceRepoUrl = this.gitExtendConfig[sourceControlType].sourceDir;
        this.sourceControlChangeForm.sourceDir = '';
      }
    },
    handleSelectedRepoUrlChange(url) {
      const match = this.gitExtendConfig[this.selectedSourceControlType];
      match.selectedRepoUrl = url;
      this.sourceControlChangeForm.sourceRepoUrl = url;
    },
    handleRepoInfoChange(data) {
      const match = this.gitExtendConfig[this.selectedSourceControlType];

      this.sourceControlChangeForm.sourceRepoUrl = data.url;
      this.sourceControlChangeForm.sourceDir = data.sourceDir;

      match.selectedRepoUrl = data.url;
      match.authInfo = {
        account: data.account,
        password: data.password,
      };
      match.sourceDir = data.sourceDir;
    },
    switchDocker() {
      this.$refs.validate2.validate().then((validator) => {
        this.switchDockerDialog.visiable = true;
      }, (validator) => {
        console.log(`${validator.field}：${validator.content}`);
      });
    },

    // 编辑镜像地址
    editDockerUrl() {
      this.isText = false;
      this.mirrorData.url = this.GLOBAL.CONFIG.MIRROR_PREFIX ? this.curAppModule.repo.repo_url.split('.com/')[1] : this.curAppModule.repo.repo_url;
    },

    async getLessCode() {
      try {
        const resp = await this.$store.dispatch('baseInfo/gitLessCodeAddress', {
          appCode: this.appCode,
          moduleName: this.curAppModule.name,
        });
        if (resp.address_in_lesscode === '' && resp.tips === '') {
          this.lessCodeFlag = false;
        }
        this.lessCodeData = resp;
      } catch (errRes) {
        this.lessCodeFlag = false;
        console.error(errRes);
      }
    },
    handleLessCode() {
      if (this.lessCodeData.address_in_lesscode) {
        return;
      }
      this.$bkMessage({ theme: 'warning', message: this.$t(this.lessCodeData.tips), delay: 2000, dismissable: false });
    },
    // 获取展示用的应用根域名，优先使用非保留的，如果没有，则选择第一个
    getAppRootDomain(clusterConf) {
      const domains = clusterConf.ingress_config.app_root_domains;
      if (domains.length === 0) {
        return '';
      }

      for (const domain of domains) {
        if (!domain.reversed) {
          return domain.name;
        }
      }
      return domains[0].name;
    },
  },
};
</script>

<style lang="scss" scoped>
    @import '~@/assets/css/mixins/border-active-logo.scss';
    .module-container{
      background: #fff;
      margin-top: 16px;
      padding: 16px 24px;
    }
    .module-info-item {
        margin-bottom: 35px;
        .title {
            color: #313238;
            font-size: 14px;
            font-weight: bold;
            line-height: 1;
            padding-bottom: 5px;
        }
        .info {
            color: #979ba5;
            font-size: 12px;
        }
        .strong {
            font-weight: normal;
            color: #63656e;
        }
        .content {
            margin-top: 20px;
            border: 1px solid #dcdee5;
            border-radius: 2px;
            &.no-border {
                border: none;
            }
            .info-special-form:nth-child(2) {
                position: relative;
                top: -4px;
            }
            .title-label {
                display: inline-block;
                padding-left: 20px;
                width: 140px;
                height: 42px;
                line-height: 42px;
                border: 1px solid #dcdee5;
                color: #313238;
                &.pl {
                    padding-left: 62px;
                }
            }
            .module-name,
            .module-init-type {
                display: inline-block;
                position: relative;
                padding-left: 16px;
                width: 821px;
                line-height: 40px;
                border-top: 1px solid #dcdee5;
                border-right: 1px solid #dcdee5;
                border-bottom: 1px solid #dcdee5;
            }
            .switcher-content {
                position: absolute;
                display: inline-block;
                margin-left: 20px;
                font-size: 12px;
                color: #979ba5;
                line-height: 24px;
            }
            .switch-button {
                margin-top: 20px;
                padding-left: 100px;
            }
            .pre-release-wrapper,
            .production-wrapper {
                display: inline-block;
                position: relative;
                width: 48%;
                border: 1px solid #dcdee5;
                border-radius: 2px;
                vertical-align: top;
                float: left;
                &.has-left {
                    float: right;
                }
                .header {
                    height: 41px;
                    line-height: 41px;
                    border-bottom: 1px solid #dcdee5;
                    background: #fafbfd;
                    .header-title {
                        margin-left: 20px;
                        color: #63656e;
                        font-weight: bold;
                        float: left;
                    }
                    .switcher-wrapper {
                        margin-right: 20px;
                        float: right;
                        .date-tip {
                            margin-right: 5px;
                            line-height: 1;
                            color: #979ba5;
                            font-size: 12px;
                        }
                    }
                }
                .ip-content {
                    padding: 14px 40px 14px 14px;
                    height: 138px;
                    overflow-x: hidden;
                    overflow-y: auto;
                    .copy-wrapper {
                        position: absolute;
                        right: 20px;
                        top: 48px;
                        font-size: 16px;
                        cursor: pointer;
                        &:hover {
                            color: #3a84ff;
                        }
                    }
                    .ip-item {
                        display: inline-block;
                        margin-left: 10px;
                        vertical-align: middle;
                    }
                    .no-ip {
                        position: absolute;
                        top: 50%;
                        left: 50%;
                        transform: translate(-50%, -50%);
                        text-align: center;
                        font-size: 12px;
                        color: #63656e;
                        p:nth-child(2) {
                            margin-top: 2px;
                        }
                    }
                }
            }
            .ip-tips {
                padding-top: 7px;
                color: #63656e;
                font-size: 12px;
                clear: both;
                i {
                    color: #ff9c01;
                }
            }
        }
    }

    .set-main-module-dialog {
        .info-p {
            margin-top: 5px;
            span {
                font-weight: bold;
            }
        }
        .a-link {
            &:hover {
                color: #699df4;
            }
        }
    }

    .establishtext {
        padding: 0 15px;
        border: solid 1px #ccc;
        border-radius: 2px;
        width: 100%;
        line-height: 40px;
        font-size: 12px;
        color: #333;
        box-sizing: border-box;
    }

    .establish-li {
        position: relative;
        margin-bottom: 8px;
        color: #999999;
        background: none;
        border-radius: 4px;
        cursor: pointer;
        &.disabled {
            color: #c4c6cc;
            cursor: not-allowed;
            span {
                color: #c4c6cc;
            }
        }
        .current {
            position: absolute;
            top: 0;
            left: 0;
            font-size: 28px;
            color: #3a84ff;
            &.set-pos {
                top: -1px;
                left: -1px;
                border-left: 1px solid #3a84ff;
                border-top: 1px solid #3a84ff;
                border-top-left-radius: 3px;
            }
        }
    }

    .establish-li.on {
        border: solid 2px #3a84ff;
        padding: 0 16px 0 14px;
    }

    .paasng-check-1 {
        float: right;
        font-size: 18px;
        font-weight: bold;
        position: relative;
        top: 13px;
    }

    .establish-li span {
        font-size: 14px;
        color: #333;
        font-weight: bold;
    }

    .establish-tab {
        &.mt {
            margin-top: 10px;
        }
    }

    .establish-list {
        margin-left: -10px;
        overflow: hidden;
        margin-right: -10px;
    }

    .establish-list li {
        float: left;
        width: 276px;
        height: 56px;
        background: #f1f3f4;
        border-radius: 2px;
        border: solid 2px #f1f3f4;
        text-align: center;
        cursor: pointer;
        margin: 0 10px;
        -webkit-transition: all .5s;
        -moz-transition: all .5s;
        -ms-transition: all .5s;
        transition: all .5s;
    }

    .establish-list li.active,
    .establish-list li:hover {
        background: #fff;
        border: solid 2px #3A84FF;
    }

    .establish-list li img {
        position: relative;
        vertical-align: middle;
        top: 13px;
    }

    .establish-list li img.establish-img2,
    .establish-list li.active img.establish-img1,
    .establish-list li:hover img.establish-img1 {
        display: none;
    }

    .establish-list li.active img.establish-img2,
    .establish-list li:hover img.establish-img2 {
        display: inline-block;
    }

    .app-main-container {
        padding: 0 30px 0 30px;
    }

.code-depot{
    display: flex;
    margin: 20px 0;
    &-item {
        width: 145px;
        height: 88px;
        background: #f0f1f5;
        border-radius: 2px;
        text-align: center;
        position: relative;
        cursor: pointer;
        img{
            width: 40px;
            height: 36px;
            margin: 12px 0 6px 0;
        }
    }
    .on {
        border: solid 2px #3A84FF;
        padding: 0 16px 0 14px;
        background-color: #fff;
        color: #3A84FF;
        @include border-active-logo;
    }
    .disabled{
        color: #c4c6cc;
        cursor: not-allowed;
        span {
            color: #c4c6cc;
        }
    }
}

.form-label {
    color: #63656e;
    line-height: 32px;
    font-size: 14px;
    padding-top: 20px;
    width: 90px;
    text-align: right;
    margin-right: 10px;
}

.en-label .form-label {
    width: 100px;
}

.form-group{
    display: flex;
    &-flex{
        width: 520px;
        margin-top: 10px;
    }
    &-radio {
        display: flex;
        align-items: center;
        margin-top: 3px;
    }
}
.bk-inline-form {
    margin: -15px 0 0 -34px;
}
.bk-form-content .form-label {
    margin-top: -7px
}
.group-prepend .group-text {
    line-height: 32px;
}
.sourceControlTypeInfo {
    white-space: nowrap;
    text-overflow: ellipsis;
    overflow: hidden;
}
.bk-form-item+.bk-form-item {
    margin-top: 13px;
}
</style>
<style lang="scss">
.form-group-flex .source-dir.error .bk-input-text {
    input {
       border-color: #ff3737 !important;
    }
}
</style>
