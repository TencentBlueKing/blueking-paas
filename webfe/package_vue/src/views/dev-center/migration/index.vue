<template lang="html">
  <div
    class="paas-content white mt50"
    :style="{ 'width': '1180px', 'margin': 'auto', 'min-height': `${minHeight}px` }"
  >
    <div class="wrap">
      <div class="right-main">
        <!-- 中间区域 start -->
        <paas-content-loader
          :is-loading="loading"
          placeholder="migration-loading"
          :height="550"
        >
          <div class="paas-migration-tit">
            <h2> {{ $t('旧应用迁移') }} </h2>
            <p> {{ $t('您可以将蓝鲸应用从旧版开发者中心迁移到新版，我们将为您提供更好的服务能力。') }} </p>
          </div>
          <!-- 迁移过程 start -->
          <div
            v-if="migrationState !== 'DEFAULT' && migrationState !== 'PRE_MIGRATION_CONFIRM'"
            class="ps-alert ps-alert-plain"
          >
            <paas-loading :is-loading="!migrationStatus.finished_migrations">
              <div slot="loadingContent">
                <div class="ps-alert-icon">
                  <i class="fa fa-wrench ps-alert-l" />
                </div>
                <div class="ps-alert-content">
                  <h4>{{ processTitle }}</h4>
                  <p
                    v-for="(operationItem, index) in migrationStatus.finished_operations"
                    :key="index"
                  >
                    <i
                      v-if="operationItem.successful"
                      class="fa fa-check"
                    />
                    <i
                      v-if="!operationItem.successful"
                      class="fa fa-times"
                    />
                    <span v-if="operationItem.apply_type === &quot;migrate&quot;"> {{ $t('执行') }} </span>
                    <span v-else> {{ $t('回滚') }} </span>
                    - {{ operationItem.description }}
                    <pre
                      v-if="!operationItem.successful"
                      class="error-detail"
                    >{{ operationItem.failed_reason }}</pre>
                  </p>
                  <!-- 执行中 -->
                  <p v-if="migrationStatus.ongoing_migration">
                    <i class="fa fa-spinner init-loading" />
                    <span v-if="migrationStatus.ongoing_migration.apply_type === &quot;migrate&quot;"> {{ $t('执行') }} </span>
                    <span v-else> {{ $t('回滚') }} </span>
                    - {{ migrationStatus.ongoing_migration.description }}
                    <pre
                      v-if="migrationStatus.ongoing_migration.log"
                      class="detail"
                    >{{ migrationStatus.ongoing_migration.log }} </pre>
                  </p>
                  <div
                    class="row spacing-x2"
                    v-dompurify-html="currentResult"
                  />
                  <div
                    class="spacing-x2"
                    style="border-bottom: solid 1px #e6e9ea"
                  />
                  <!-- 迁移中 -->
                  <div
                    v-show="migrationStatus.is_active"
                    class="row spacing-x2"
                  >
                    {{ $t('在当前迁移流程完成前 [执行迁移-部署新应用-访问新应用-测试验证-确认迁移]，你将无法开始新的迁移工作。') }}
                  </div>

                  <!-- 迁移结束 -->
                  <div
                    v-show="migrationState === 'DONE_MIGRATION' "
                    class="row spacing-x2"
                  >
                    <p> {{ $t('接下来，您需要：') }} </p>
                    <template v-if="migrationFlagObj.is_third_app">
                      <p>
                        {{ $t('1. 在新版开发者中心确认应用第三方地址是否正确') }}
                        <router-link
                          class="ps-link"
                          :to="{ name: 'appMarket', params: { id: currentMigrationId, moduleId: 'default' } }"
                        >
                          <i class="paasng-icon paasng-angle-double-right" /> {{ $t('访问应用') }}
                        </router-link>
                      </p>
                      <p>{{ $t('2. 当你确认一切功能正常运行后，便可以点击【确认迁移】按钮来完成迁移。') }}</p>
                    </template>
                    <template v-else>
                      <p>
                        {{ $t('1. 在新版开发者中心部署应用，并确认应用功能都正常') }}
                        <router-link
                          class="ps-link"
                          :to="{ name: 'appDeployForStag', params: { id: currentMigrationId, moduleId: 'default' } }"
                        >
                          <i class="paasng-icon paasng-angle-double-right" /> {{ $t('现在去部署') }}
                        </router-link>
                      </p>
                      <p>{{ $t('2. 当你确认一切功能正常运行后，便可以点击【确认迁移】按钮来完成迁移。') }}</p>
                      <p style="color: #ff0000">
                        {{ $t('“确认迁移”') }}&nbsp;{{ $t('将会停掉旧版本中的服务进程，并切换应用访问入口。') }}
                        <template v-if="!migrationStatus.is_v3_prod_available">
                          {{ $t('已下架的应用桌面无法查看，重新部署生产环境可上架到桌面。') }}
                        </template>
                      </p>
                    </template>
                    <p>
                      <!-- 第三方应用可以直接确认迁移 -->
                      <template v-if="migrationFlagObj.is_third_app">
                        <a
                          class="ps-btn ps-btn-primary ps-btn-margin"
                          href="###"
                          @click="confirmMigrationFinished"
                        > {{ $t('确认迁移') }} </a>
                      </template>
                      <template v-else-if="(migrationStatus.is_v3_prod_available || migrationStatus.is_v3_stag_available) && confirmBtnEnabled">
                        <a
                          v-if="!migrationFlagObj.is_prod_deployed && !migrationFlagObj.is_stag_deployed"
                          class="ps-btn ps-btn-primary ps-btn-margin"
                          href="###"
                          @click="confirmMigrationFinished"
                        > {{ $t('确认迁移') }} </a>
                        <template v-else>
                          <bk-popover placement="top">
                            <a
                              class="ps-btn ps-btn-primary ps-btn-margin"
                              disabled
                              href="###"
                            > {{ $t('确认迁移') }} </a>
                            <div slot="content">
                              <p>
                                {{ migrationFlagObj.is_prod_deployed && migrationFlagObj.is_stag_deployed
                                  ? $t('应用在旧版开发者中心的测试环境和正式环境都未下架') : migrationFlagObj.is_prod_deployed && !migrationFlagObj.is_stag_deployed ? $t('应用在旧版开发者中心的正式环境未下架') : $t('应用在旧版开发者中心的测试环境未下架') }}
                                <a
                                  :href="migrationFlagObj.offline_url"
                                  target="_blank"
                                  class="blue"
                                > {{ $t('现在去下架') }} </a>
                              </p>
                            </div>
                          </bk-popover>
                        </template>
                      </template>
                      <template v-else>
                        <bk-popover placement="top">
                          <a
                            class="ps-btn ps-btn-primary ps-btn-margin"
                            disabled
                            href="###"
                          > {{ $t('确认迁移') }} </a>
                          <div slot="content">
                            <p>
                              {{ $t('请先部署应用并确认功能正常') }}
                              <router-link
                                class="ps-link"
                                :to="{ name: 'appDeployForStag', params: { id: currentMigrationId, moduleId: 'default' } }"
                              >
                                <i class="paasng-icon paasng-angle-double-right" /> {{ $t('现在去部署') }}
                              </router-link>
                            </p>
                          </div>
                        </bk-popover>
                      </template>
                      <a
                        v-if="!migrationStatus.is_v3_prod_available && !migrationStatus.is_v3_stag_available"
                        href="###"
                        class="ps-btn ps-btn-l ps-btn-link"
                        @click="rollbackCurrent"
                      > {{ $t('经测试功能不正确，取消本次迁移') }} </a>
                      <template v-else>
                        <bk-popover placement="top">
                          <a
                            class="ps-btn ps-btn-primary ps-btn-margin"
                            disabled
                            href="###"
                          > {{ $t('经测试功能不正确，取消本次迁移') }} </a>
                          <div slot="content">
                            <p>
                              {{ migrationStatus.is_v3_prod_available && migrationStatus.is_v3_stag_available
                                ? $t('应用预发布环境和生产环境都未下架') : migrationStatus.is_v3_prod_available && !migrationStatus.is_v3_stag_available ? $t('应用生产环境未下架') : $t('应用预发布环境未下架') }}
                              <router-link
                                class="ps-link"
                                :to="{ name: migrationStatus.is_v3_prod_available && !migrationStatus.is_v3_stag_available ? 'appDeployForProd' : 'appDeployForStag', params: { id: currentMigrationId, moduleId: 'default' } }"
                              >
                                {{ $t('现在去下架') }}
                              </router-link>
                            </p>
                          </div>
                        </bk-popover>
                      </template>
                    </p>
                  </div>
                </div>
              </div>
            </paas-loading>
          </div>
          <!-- 迁移过程 end -->
          <div class="environment-list app-category">
            <a
              :class="{ 'active': currentEnv === 'todoMigrate' }"
              @click="changeTabList('todoMigrate')"
            > {{ $t('未完成迁移应用') }} ({{ todoAppList.length }})</a>
            <a
              :class="{ 'active': currentEnv === 'doneMigrate' }"
              @click="changeTabList('doneMigrate')"
            > {{ $t('已迁移应用') }} ({{ doneAppList.length }})</a>
            <a
              :class="{ 'active': currentEnv === 'cannotMigrate' }"
              @click="changeTabList('cannotMigrate')"
            > {{ $t('暂不支持迁移应用') }} ({{ cannotAppList.length }})</a>
          </div>
          <div>
            <!-- 未完成迁移应用 start -->
            <div
              v-show="currentEnv === 'todoMigrate'"
              class="environment"
            >
              <table class="ps-table ps-table-simple">
                <colgroup>
                  <col style="width: 20%">
                  <col style="width: 10%">
                  <col style="width: 10%">
                  <col style="width: 15%">
                  <col style="width: 10%">
                  <col style="width: 10%">
                  <col style="width: 20%">
                </colgroup>
                <tr>
                  <th class="pl30">
                    {{ $t('蓝鲸应用') }}
                  </th>
                  <th> {{ $t('开发语言') }} </th>
                  <th> {{ $t('版本') }} </th>
                  <th> {{ $t('创建时间') }} </th>
                  <th class="center">
                    {{ $t('蓝鲸桌面') }}
                  </th>
                  <th class="center">
                    {{ $t('迁移状态') }}
                  </th>
                  <th class="center">
                    {{ $t('操作') }}
                  </th>
                </tr>
                <tr
                  v-for="(appItem, appItemIndex) in todoAppList"
                  :key="appItemIndex"
                >
                  <td class="pl30">
                    <a
                      :href="appItem.legacy_url"
                      class="ps-table-app"
                    >
                      <!-- <img :src="appItem.logo" class="fleft applogo"> -->
                      <fallback-image
                        :url="appItem.logo"
                        :url-fallback="defaultLogo"
                        class="fleft applogo"
                      />
                      <span class="app-name-text">{{ appItem.name }}</span>
                      <span class="app-code-text">{{ appItem.code }}</span>
                    </a>
                  </td>
                  <td>{{ appItem.language }}</td>
                  <td>{{ appItem.region }}</td>
                  <td>{{ appItem.created }}</td>
                  <td class="center">
                    {{ appItem.is_prod_deployed ? $t('已上架') : $t('未上架') }}
                  </td>
                  <td class="center">
                    {{ appItem.is_active ? $t('进行中') : $t('未启动') }}
                  </td>
                  <td class="center">
                    <span
                      v-if="!appItem.is_active"
                      v-bk-tooltips="{
                        content: $t('当前有其他应用（{id}）正在迁移，需待迁移完成后才能开启新应用的迁移。', { id: currentApp.code }),
                        disabled: !isMigrateButtonDisabled
                      }"
                    >
                      <button
                        class="ps-btn ps-btn-primary"
                        :disabled="isMigrateButtonDisabled"
                        @click="makeMigration(appItem)"
                      >
                        <span> {{ $t('迁移到') }} </span> {{ $t('新版开发者中心') }}
                      </button>
                    </span>
                    <button
                      v-else
                      class="ps-btn ps-btn-primary"
                      @click="viewMigrationStatus(appItem)"
                    >
                      {{ $t('查看进度') }}
                    </button>
                  </td>
                </tr>
                <tr v-if="todoAppList.length === 0">
                  <td
                    colspan="7"
                    class="center"
                  >
                    <div class="ps-no-result">
                      <div class="text">
                        <table-empty
                          :empty-title="$t('暂无应用')"
                          empty
                        />
                      </div>
                    </div>
                  </td>
                </tr>
              </table>
            </div>
            <!-- 未完成迁移应用 end -->

            <!-- 已迁移应用 start -->
            <div
              v-show="currentEnv === 'doneMigrate'"
              class="environment"
            >
              <table class="ps-table  ps-table-simple">
                <colgroup>
                  <col style="width: 25%">
                  <col style="width: 10%">
                  <col style="width: 15%">
                  <col style="width: 20%">
                  <col style="width: 10%">
                  <col style="width: 20%">
                </colgroup>
                <tr>
                  <th class="pl30">
                    {{ $t('蓝鲸应用') }}
                  </th>
                  <th> {{ $t('开发语言') }} </th>
                  <th> {{ $t('版本') }} </th>
                  <th> {{ $t('迁移时间') }} </th>
                  <th class="center">
                    {{ $t('蓝鲸桌面') }}
                  </th>
                  <th class="center">
                    {{ $t('操作') }}
                  </th>
                </tr>
                <tr
                  v-for="(appItem, appItemIndex) in doneAppList"
                  :key="appItemIndex"
                >
                  <td class="pl30">
                    <router-link :to="{ name: `appSummary`, params: { id: appItem.code }}">
                      <a class="ps-table-app">
                        <fallback-image
                          :url="appItem.logo"
                          :url-fallback="defaultLogo"
                          class="fleft applogo"
                        />
                        <span class="app-name-text">{{ appItem.name }}</span>
                        <span class="app-code-text">{{ appItem.code }}</span>
                      </a>
                    </router-link>
                  </td>
                  <td>{{ appItem.language }}</td>
                  <td>{{ appItem.region }}</td>
                  <td>{{ appItem.migration_finished_date }}</td>
                  <td class="center">
                    {{ appItem.is_prod_deployed ? $t('已上架') : $t('未上架') }}
                  </td>
                  <td class="center">
                    <a
                      href="###"
                      class="ps-btn ps-btn-primary"
                      :disabled="migrationStatus.is_active || !appItem.has_prod_deployed_before_migration"
                      @click="rollbackMigrationBtnClick(appItem)"
                    > {{ $t('回滚至旧版本') }} </a>
                  </td>
                </tr>
                <tr v-if="doneAppList.length === 0">
                  <td
                    colspan="6"
                    class="center"
                  >
                    <div class="ps-no-result">
                      <div class="text">
                        <table-empty
                          :empty-title="$t('暂无应用')"
                          empty
                        />
                      </div>
                    </div>
                  </td>
                </tr>
              </table>
            </div>
            <!-- 已迁移应用 end -->

            <!-- 暂不支持迁移应用 start -->
            <div
              v-show="currentEnv === 'cannotMigrate'"
              class="environment"
            >
              <table class="ps-table ps-table-simple">
                <colgroup>
                  <col style="width: 25%">
                  <col style="width: 10%">
                  <col style="width: 10%">
                  <col style="width: 20%">
                  <col style="width: 35%">
                </colgroup>
                <tr>
                  <th class="pl30">
                    {{ $t('蓝鲸应用') }}
                  </th>
                  <th> {{ $t('开发语言') }} </th>
                  <th> {{ $t('版本') }} </th>
                  <th> {{ $t('创建时间') }} </th>
                  <th> {{ $t('原因') }} </th>
                </tr>

                <tr
                  v-for="(appItem, appItemIndex) in cannotAppList"
                  :key="appItemIndex"
                >
                  <td class="pl30">
                    <a
                      :href="appItem.legacy_url"
                      class="ps-table-app"
                    >
                      <!-- <img :src="appItem.logo" class="fleft applogo"> -->
                      <fallback-image
                        :url="appItem.logo"
                        :url-fallback="defaultLogo"
                        class="fleft applogo"
                      />
                      <span class="app-name-text">{{ appItem.name }}</span>
                      <span class="app-code-text">{{ appItem.code }}</span>
                    </a>
                  </td>
                  <td>{{ appItem.language }}</td>
                  <td>{{ appItem.region }}</td>
                  <td>{{ appItem.created }}</td>
                  <td>
                    <ul>
                      <li
                        v-for="(reason, reasonIndex) in appItem.not_support_reasons"
                        :key="reasonIndex"
                      >
                        {{ reason }}
                      </li>
                    </ul>
                  </td>
                </tr>
                <tr v-if="cannotAppList.length === 0">
                  <td
                    colspan="5"
                    class="center"
                  >
                    <div class="ps-no-result">
                      <div class="text">
                        <table-empty
                          :empty-title="$t('暂无应用')"
                          empty
                        />
                      </div>
                    </div>
                  </td>
                </tr>
              </table>
            </div>
            <!-- 暂不支持迁移应用 end -->
          </div>
        </paas-content-loader>

        <bk-dialog
          v-model="confirmDialog.visiable"
          width="800"
          :title="$t(`迁移应用【{name}】到新版开发者中心`, { name: currentApp.name })"
          :theme="'primary'"
          :mask-close="false"
          :loading="confirmDialog.isLoading"
          @after-close="afterDialogClose"
        >
          <form
            v-show="migrationState === 'PRE_MIGRATION_CONFIRM'"
            id=""
            class="ps-form"
            method="POST"
            action="javascript:;"
          >
            <div class="ps-form-content">
              <div class="ps-form-group">
                <p>
                  {{ $t('开始前，请确认应用') }} 【{{ currentApp.name }}】 {{ $t('满足以下迁移前置条件，如果不满足，请联系') }} 【<a
                    v-if="GLOBAL.HELPER.href"
                    :href="GLOBAL.HELPER.href"
                  >{{ GLOBAL.HELPER.name }}</a><span v-else> {{ $t('管理员') }} </span>】， {{ $t('我们将单独处理您的迁移请求。') }}
                </p>
                <p class="ps-form-item">
                  <label><input
                    v-model="noOutterAuthorize"
                    type="checkbox"
                    class="ps-checkbox-default"
                    @change="readmeCheckboxChanged()"
                  ></label>
                  <span class="ps-form-text"> {{ $t('应用没有访问某些添加了IP白名单的服务') }} <br>
                    <span class="ps-form-text-gray"> {{ $t('应用迁移到新版开发者中心后，出口IP将会发生变化') }} </span>
                  </span>
                </p>
                <p class="ps-form-item">
                  <label><input
                    v-model="noOutterDb"
                    type="checkbox"
                    class="ps-checkbox-default"
                    @change="readmeCheckboxChanged()"
                  ></label>
                  <span class="ps-form-text"> {{ $t('应用没有使用外部 DB') }} <br>
                    <span class="ps-form-text-gray"> {{ $t('如果使用外部DB, 需要根据') }} <a
                      target="_blank"
                      :href="GLOBAL.DOC.LEGACY_MIGRATION"
                    > {{ $t('迁移文档') }} </a> {{ $t('的指引操作') }} </span>
                  </span>
                </p>
                <p class="ps-form-item">
                  <label><input
                    v-model="noStacklessPython"
                    type="checkbox"
                    class="ps-checkbox-default"
                    @change="readmeCheckboxChanged()"
                  ></label>
                  <span class="ps-form-text"> {{ $t('应用没有使用 Stackless Python 的相关特性') }} </span>
                </p>
                <p class="ps-form-item">
                  <label><input
                    v-model="noNfsOrFileupload"
                    type="checkbox"
                    class="ps-checkbox-default"
                    @change="readmeCheckboxChanged()"
                  ></label>
                  <span class="ps-form-text"> {{ $t('应用没有使用NFS服务（之前的文件上传采用的NFS）') }} </span>
                </p>
                <div>
                  <p class="ps-form-item">
                    <label><input
                      v-model="noApiGateway"
                      type="checkbox"
                      class="ps-checkbox-default"
                      @change="readmeCheckboxChanged()"
                    ></label>
                    <span class="ps-form-text"> {{ $t('应用如果对外提供了接口，需要通知调用方修改接口url') }} </span><br>
                  </p>
                  <span class="ps-form-info">1. {{ $t('没有使用api gateway，需要通知所有使用到接口的应用或服务 修改url') }}</span><br>
                  <span class="ps-form-info">2. {{ $t('使用了api gateway, 只需要再api gateway 上修改url即可') }}</span>
                </div>
                <p class="ps-form-item">
                  <label><input
                    v-model="noOutterLink"
                    type="checkbox"
                    class="ps-checkbox-default"
                    @change="readmeCheckboxChanged()"
                  ></label>
                  <span class="ps-form-text"> {{ $t('发给其他人或第三方系统的回调链接需要修改，比如邮件中的链接，权限审批链接等') }} </span>
                </p>
                <p class="ps-form-item">
                  <label><input
                    v-model="finshedMigrationReadme"
                    type="checkbox"
                    class="ps-checkbox-default"
                    @change="readmeCheckboxChanged()"
                  ></label>
                  <span class="ps-form-text">
                    {{ $t('已阅读') }}
                    <span
                      class="legacy-title"
                      @click.stop="appLegacy"
                    > {{ $t('迁移文档') }} </span>
                  </span>
                </p>
                <p class="migrate-note">
                  {{ $t('点击【开启迁移】后，你的应用服务将不会受到任何影响') }}
                </p>
              </div>
            </div>
          </form>
          <div slot="footer">
            <bk-button
              theme="primary"
              :disabled="!bAllPreConfirmChecked"
              @click="startMigration"
            >
              <span
                v-if="!bAllPreConfirmChecked"
                v-bk-tooltips="$t('请确认迁移注意事项')"
              > {{ $t('开启迁移') }} </span>
              <span v-else> {{ $t('开启迁移') }} </span>
            </bk-button>
            <bk-button
              style="margin-left: 6px;"
              @click="cancelMigration"
            >
              {{ $t('取消') }}
            </bk-button>
          </div>
        </bk-dialog>
      </div>
    </div>
    <!-- 确认迁移 二次确认弹窗 -->
    <bk-dialog
      v-model="delAppDialog.visiable"
      width="540"
      :title="$t('确认迁移？')"
      :theme="'primary'"
      :mask-close="false"
      :loading="delAppDialog.isLoading"
      @after-leave="hookAfterClose"
    >
      <form
        class="ps-form"
        style="width: 480px;"
        @submit.prevent="submitMigrateApp"
      >
        <div class="spacing-x1">
          {{ $t('该操作 ') }} <span style="font-weight: bold;"> {{ $t('无法撤回') }} </span> 。{{ $t('请在严格验证应用网页端、移动端等可以正常访问后，输入应用 ID') }} <code>{{ currentMigrationId }}</code> {{ $t('确认迁移：') }}
        </div>
        <div class="ps-form-group">
          <input
            v-model="formRemoveConfirmId"
            type="text"
            class="ps-form-control"
          >
        </div>
      </form>
      <template slot="footer">
        <bk-button
          theme="primary"
          :disabled="!formRemoveValidated"
          @click="submitMigrateApp"
        >
          {{ $t('确定') }}
        </bk-button>
        <bk-button
          theme="default"
          @click="delAppDialog.visiable = false"
        >
          {{ $t('取消') }}
        </bk-button>
      </template>
    </bk-dialog>
  </div>
</template>

<script>
import FallbackImage from '@/components/ui/fallback-image';
import defaultLogo from '../../../../static/images/default_logo.png';

export default {
  components: {
    FallbackImage,
  },
  data() {
    return {
      loading: true,
      currentEnv: '',
      currentResult: '',
      processTitle: '',
      todoAppList: [],
      doneAppList: [],
      cannotAppList: [],
      migrationState: 'DEFAULT', // 参考 valueToStatusCode 方法
      taskConfirmed: false,
      minHeight: 550,
      bAllPreConfirmChecked: false,
      noOutterAuthorize: false,
      noOutterDb: false,
      noStacklessPython: false,
      noNfsOrFileupload: false,
      noApiGateway: false,
      noOutterLink: false,
      finshedMigrationReadme: false,
      confirmBtnEnabled: true,
      currentLegacyAppID: 0,
      currentMigrationID: 0,
      currentApp: {},
      migrateType: this.$t('迁移'),
      migrationStatus: {
        name: '',
        status: 0,
        ongoing_migration: {
          name: '',
        },
        finished_migration: [],
      },
      confirmDialog: {
        visiable: false,
        isLoading: false,
      },
      delAppDialog: {
        visiable: false,
        isLoading: false,
      },
      formRemoveConfirmId: '',
      currentMigrationId: '',
      migrationFlagObj: {
        is_prod_deployed: false,
        is_stag_deployed: false,
        offline_url: '',
        is_third_app: false,
      },
      defaultLogo,
    };
  },
  computed: {
    formRemoveValidated() {
      return this.currentMigrationId.toString() === this.formRemoveConfirmId.toString();
    },
    isMigrateButtonDisabled() {
      return ['ON_MIGRATION', 'ON_ROLLBACK', 'ON_CONFIRMING', 'DONE_MIGRATION'].includes(this.migrationState);
    },
  },
  created() {
    this.init();
  },
  mounted() {
    const HEADER_HEIGHT = 50;
    const FOOTER_HEIGHT = 70;
    const winHeight = window.innerHeight;
    const contentHeight = winHeight - HEADER_HEIGHT - FOOTER_HEIGHT;
    if (contentHeight > this.minHeight) {
      this.minHeight = contentHeight;
    }
  },
  methods: {
    appLegacy() {
      window.open(this.GLOBAL.DOC.LEGACY_MIGRATION);
    },
    submitMigrateApp() {
      this.delAppDialog.visiable = false;
      this.confirmBtnEnabled = false;
      // 切换接入层
      this.migrateType = this.$t('切接入层');
      const url = `${BACKEND_URL}/api/mgrlegacy/migrations/progress/${this.currentMigrationID}/confirm/`;
      this.$http.post(url, {}).then((response) => {
        this.pollMigration();
      })
        .catch((e) => {
          this.$paasMessage({
            theme: 'error',
            message: e.detail || e.message || this.$t('接口异常'),
          });
        });
    },
    hookAfterClose() {
      this.formRemoveConfirmId = '';
    },
    reset() {
      this.currentResult = '';
      this.noOutterAuthorize = false;
      this.noOutterDb = false;
      this.noStacklessPython = false;
      this.noNfsOrFileupload = false;
      this.noApiGateway = false;
      this.noOutterLink = false;
      this.finshedMigrationReadme = false;
      this.currentLegacyAppID = 0;
      this.migrationState = 'DEFAULT';
      this.bAllPreConfirmChecked = false;
      this.confirmBtnEnabled = true;

      this.currentApp = null;
      this.currentMigrationId = '';
      this.currentMigrationID = 0;
      this.currentApp = {};
      this.migrateType = this.$t('迁移');
      this.migrationStatus = {
        name: '',
        status: 0,
        ongoing_migration: {
          name: '',
        },
        finished_migration: [],
      };
    },
    init() {
      this.currentEnv = this.$route.query.focus || 'todoMigrate';
      this.initAppList();
    },
    initAppList() {
      this.loading = true;
      this.loadAppList();
    },
    loadAppList() {
      // TODO 更新应用列表的数据
      const url = `${BACKEND_URL}/api/mgrlegacy/applications/?result_type=all`;
      this.$http.get(url).then((response) => {
        this.loading = false;
        const results = response.data || [];
        this.todoAppList = results.filter(item => item.category === 'todoMigrate');
        this.doneAppList = results.filter(item => item.category === 'doneMigrate');
        this.cannotAppList = results.filter(item => item.category === 'cannotMigrate');

        // 加载正在活跃操作
        const activeApp = this.todoAppList.find(app => app.is_active && app.latest_migration_id !== undefined);
        if (activeApp && this.currentMigrationID !== activeApp.latest_migration_id) {
          this.currentApp = activeApp;
          this.currentMigrationId = activeApp.code;
          this.currentMigrationID = activeApp.latest_migration_id;

          if (this.migrationState === 'ON_ROLLBACK') {
            this.migrateType = this.$t('回滚');
          }

          this.processTitle = this.$t('应用[{name}] 正在进行{type}...', {
            name: this.currentApp.name,
            type: this.migrateType,
          });

          this.pollMigration();
          this.fetchMigrationFlag();
        }
      });
    },
    changeTabList(type) {
      this.currentEnv = type;
    },
    valueToStatusCode(value) {
      // PRE_MIGRATION_CONFIRM 为前端状态
      const valueMap = {
        0: 'DEFAULT',
        1: 'ON_MIGRATION',
        2: 'FAILED',
        3: 'DONE_MIGRATION',
        4: 'ON_ROLLBACK',
        5: 'ROLLBACKED',
        6: 'ON_CONFIRMING',
        7: 'CONFIRMED',
      };
      return valueMap[value];
    },
    viewMigrationStatus(appItem) {
      this.reset();
      this.currentLegacyAppID = appItem.legacy_app_id;

      this.currentMigrationId = appItem.code;

      this.currentApp = this.todoAppList.find(item => item.legacy_app_id === this.currentLegacyAppID);
      this.currentMigrationID = this.currentApp.latest_migration_id;
      this.migrationState = this.currentApp.tag;
      this.pollMigration();
    },
    startMigration() {
      if (!this.bAllPreConfirmChecked) {
        return;
      }

      this.processTitle = this.$t('应用[{name}] 正在进行{type}...', { name: this.currentApp.name, type: this.migrateType });
      // TODO: show loading icon
      // this.$refs.confirmModal.close()
      this.confirmDialog.visiable = true;

      this.migrateType = this.$t('迁移');
      this.migrationState = 'ON_MIGRATION';
      const url = `${BACKEND_URL}/api/mgrlegacy/migrations/progress/`;
      this.$http.post(url, { legacy_app_id: this.currentLegacyAppID }).then((response) => {
        // 提示迁移任务创建成功
        const resData = response;
        this.currentMigrationID = resData.id;
        this.confirmDialog.visiable = false;
        this.pollMigration();
        this.fetchMigrationFlag();
      });
    },
    fetchMigrationFlag() {
      const url = `${BACKEND_URL}/api/mgrlegacy/migrations/progress/${this.currentMigrationID}/old_state/`;
      this.$http.get(url).then((response) => {
        this.migrationFlagObj = Object.assign({}, response);
      });
    },
    pollMigration() {
      if (this.$route.name !== 'appLegacyMigration') {
        return;
      }
      // 初始化任务状态
      this.taskConfirmed = false;
      // 轮询任务
      // get status
      const url = `${BACKEND_URL}/api/mgrlegacy/migrations/progress/${this.currentMigrationID}/state/`;
      this.$http.get(url).then((response) => {
        // 更新迁移状态
        const resData = response;
        this.migrationStatus = resData;

        // 防止来回切换导致混乱情况
        if (this.migrationStatus.id !== this.currentMigrationID) {
          return;
        }

        // update front end status
        this.migrationState = this.valueToStatusCode(this.migrationStatus.status);

        // NOTE: pull
        // ON_MIGRATION = 1
        // ON_ROLLBACK = 4
        // ON_CONFIRMING = 6

        // NOTE: not pull
        // DEFAULT = 0
        // FAILED = 2
        // DONE_MIGRATION = 3
        // ROLLBACKED = 5
        // CONFIRMED = 7
        // # 回滚失败, 需要人工介入
        // ROLLBACK_FAILED = 8

        const status = this.migrationState;
        if (status === 'DONE_MIGRATION') {
          // 成功 - DONE_MIGRATION
          const msg = this.$t('信息同步完成！');
          this.currentResult = msg;
          this.confirmBtnEnabled = true;
          return;
        } if (status === 'FAILED') {
          // 失败并自动回滚完成
          const lastIdx = this.migrationStatus.finished_migrations.length - 1;
          const msg = `${this.$t('迁移步骤: ')}<${resData.finished_migrations[lastIdx].description}> ${this.$t('执行失败, 回滚完成！')}`;

          const msgWithDoc = `${msg}<br>${this.$t('失败原因请参考')}<a href="" class="ps-btn ps-btn-l ps-btn-link">${this.$t('相关文档')}</a>`;
          this.currentResult = msgWithDoc;
          this.processTitle = this.$t('应用迁移失败！');
          this.$bkInfo({
            theme: 'error',
            title: msg,
          });
        } else if (status === 'ROLLBACKED') {
          // 人工点回滚执行完成
          this.currentResult = this.$t('迁移失败需要回滚，回滚完成！');
          this.processTitle = this.$t('应用回滚完成！');
          this.initAppList();
          this.confirmBtnEnabled = true;
          return;
        } else if (status === 'CONFIRMED') {
          this.taskConfirmed = true;
          // 已结束的, 不继续拉
          this.currentResult = this.$t('恭喜您，应用迁移到新版开发者中心完成了！');
          this.processTitle = this.$t('应用迁移完成！');
          this.initAppList();
          this.confirmBtnEnabled = true;
          return;
        } else if (status === 'ROLLBACK_FAILED') {
          this.currentResult = `${this.$t('回滚失败，请联系')}${this.GLOBAL.HELPER.name}！}`;
          this.processTitle = this.$t('应用回滚失败！');
          this.confirmBtnEnabled = true;
          return;
        }

        if (status === 'ON_ROLLBACK') {
          this.currentResult = this.$t('迁移失败需要回滚，执行回滚！');
        }

        // polling next
        setTimeout(this.pollMigration, 3000);
      });
    },
    readmeCheckboxChanged() {
      // 迁移须知文档中的checkbox有变动时需要对应修改页面迁移按钮的可用状态
      if (this.noOutterAuthorize && this.noOutterDb && this.noStacklessPython && this.noNfsOrFileupload && this.noApiGateway && this.finshedMigrationReadme && this.noOutterLink) {
        this.bAllPreConfirmChecked = true;
      } else {
        this.bAllPreConfirmChecked = false;
      }
    },
    cancelMigration() {
      // this.$refs.confirmModal.close()
      this.confirmDialog.visiable = false;
    },
    afterDialogClose() {
      this.reset();
    },
    makeMigration(appItem) {
      // legacy_app_id
      this.reset();

      // 显示确认框
      this.migrationState = 'PRE_MIGRATION_CONFIRM';

      this.currentMigrationId = appItem.code;

      this.currentLegacyAppID = appItem.legacy_app_id;
      this.currentApp = this.todoAppList.find(item => item.legacy_app_id === this.currentLegacyAppID);

      this.confirmDialog.visiable = true;
    },
    confirmMigrationFinished() {
      this.delAppDialog.visiable = true;
    },
    rollbackCurrent() {
      this.$bkInfo({
        title: this.$t('取消本次迁移？'),
        subTitle: this.$t('取消后将下架并删除在新版开发者中心创建的应用'),
        extCls: 'paas-roll-back-info-cls',
        closeIcon: false,
        confirmFn: () => {
          // 回滚当前的迁移
          this.migrateType = this.$t('回滚');
          this.rollbackMigration(this.currentMigrationID);
        },
      });
    },
    rollbackMigration(migrationProcessID) {
      this.processTitle = this.$t('应用[{name}] 正在进行{type}...', { name: this.currentApp.name, type: this.migrateType });
      // 迁移完成列表中的回滚，这时已经切换接入层
      const url = `${BACKEND_URL}/api/mgrlegacy/migrations/progress/${migrationProcessID}/rollback/`;
      this.$http.post(url, {}).then((response) => {
        this.currentMigrationID = migrationProcessID;
        this.migrationState = 'ON_MIGRATION';
        this.pollMigration();
      })
        .catch((e) => {
          this.$paasMessage({
            theme: 'error',
            message: e.detail || e.message || this.$t('接口异常'),
          });
        });
    },
    rollbackMigrationBtnClick(appItem) {
      if (this.migrationStatus.is_active || !appItem.has_prod_deployed_before_migration) {
        return false;
      }
      const migrationProcessID = appItem.latest_migration_id;
      // 加载当前app
      this.currentApp = this.doneAppList.find(item => item.latest_migration_id === migrationProcessID);
      const self = this;
      this.$bkInfo({
        title: this.$t('确认要回滚至旧版本？'),
        confirmFn() {
          // 启动回滚
          self.rollbackMigration(migrationProcessID);
        },
      });
    },
  },
};
</script>

<style lang="scss" scoped>
    .legacy-title {
        color: #3a84ff;
        cursor: pointer;
        &:hover {
            color: #699df4;
        }
    }
    .error-detail {
        color: #ff0000;
    }

    .ps-alert-plain {
        background-color: #fff;
        color: #666;
    }

    .ps-alert {
        h4 {
            font-weight: normal;
        }
    }

    .migrate-note {
        font-weight: bold;
    }

    .middle {
        margin-bottom: 20px;

        p {
            line-height: 46px;
        }
    }

    .ps-table-app {
        color: #666;

        &:hover {
            color: #3a84ff;
        }
    }

    .ps-link {
        margin-left: 4px;
        color: #3a84ff;
        i {
            color: #3a84ff;
        }
    }

    .app-name-text {
        display: inline-block;
        width: 130px;
        vertical-align: top;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }

    .app-name-text em {
        display: inline-block;
        vertical-align: middle;
        line-height: 16px;
    }

    .app-code-text {
        display: inline-block;
        width: 130px;
        color: #999;
        vertical-align: top;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .app-code-text em {
        display: inline-block;
        vertical-align: middle;
        line-height: 16px;
    }

    .applogo {
        width: 36px;
        height: 36px;
        border-radius: 4px;
        margin-right: 13px;
        float: left;
    }

    .p5 {
        padding: 0 5px;
    }

    .ps-table {
        width: 100%;
    }

    .ps-table tr {
        background: #f3f5f5;

        &:nth-child(2n) {
            background: #fff;
        }
    }

    .ps-table th.pl30,
    .ps-table td.pl30 {
        padding-left: 30px;
    }

    .environment {
        width: 100%;
    }

    .environment-list a {
        width: 33.333%;
        cursor: pointer;
    }

    .app-category {
        a {
            border-bottom: 3px solid transparent;

            &:hover {
                color: #3A84FF;
            }
        }
    }

    .ps-btn-link {
        text-decoration: underline !important;
    }

    .ps-alert-content {
        width: 90%;

        p {
            line-height: 24px;
            color: #666;
        }

        .fa {
            color: #30d878;
            margin-right: 5px;
        }
    }

    .ps-alert-icon i {
        color: #666;
    }

    .init-loading {
        animation: round .8s infinite linear;
    }

    @keyframes round {
        0% {
            transform: rotate(0);
        }

        100% {
            transform: rotate(360deg);
        }
    }

    .ps-btn-margin {
        margin: 12px 8px 0 0;
    }

    .ps-form {
        width: 600px;
        margin: 0 auto;
    }

    .ps-form-title {
        width: 100%;
        display: inline-block;
        font-size: 22px;
        color: #333;
        text-align: center;
        line-height: 34px;
        padding-bottom: 15px;
    }

    .ps-form-button {
        text-align: right;
        padding: 12px 10px 12px 0;
        border-top: solid 1px #e5e5e5;
        margin-top: 15px;
    }

    .reset-button {
        a {
            width: 78px;
        }
    }

    .ps-form-title-move {
        font-size: 18px;
        padding: 15px;
        border-bottom: solid 1px #e5e5e5;
    }

    .ps-form-group {
        color: #666;

        p {
            padding: 5px 0;
            line-height: 24px;
        }

        label {
            display: inline-block;
            vertical-align: top;
        }
    }

    .ps-form-text {
        display: inline-block;
        position: relative;
        top: -4px;
        color: #666;

        .ps-form-text-gray {
            color: #ffc349;
        }
    }

    .ps-form-content {
        padding: 5px 15px 0 15px;

        p {
            font-size: 14px;
            color: #666;
        }
    }

    .paas-migration-tit {
        padding: 5px 0 11px 0;
        color: #666;
        position: relative;

        h2 {
            font-size: 18px;
            font-weight: normal;
            line-height: 36px;
            color: #4f515e;
        }

        p {
            font-size: 14px;
            color: #7b7d8a;
            margin: 5px 0;
        }
    }

    .ps-checkbox-default:after {
        box-sizing: content-box;
    }

    .ps-form-item {
        display: flex;
    }

    .ps-form-info {
        display: inline-block;
        padding-left: 25px;
    }
</style>
