<template lang="html">
  <div class="right-main">
    <paas-content-loader
      :class="contentClass"
      :is-loading="loading"
      placeholder="roles-loading"
    >
      <div class="header">
        <div class="flex-row align-items-center">
          <bk-button
            v-if="enableToAddRole"
            theme="primary"
            icon="plus"
            class="mr12"
            @click="toggleMemberSideslider(true, 'add')"
          >
            {{ $t('新增成员') }}
          </bk-button>
          <!-- 胶囊tab筛选 -->
          <CustomRadioCapsule
            class="mr12"
            :list="filterList"
            v-model="selectedRole"
            @change="handlerFilterChange"
          >
            <template slot-scope="{ item }">{{ `${item.label}（${item.count}）` }}</template>
          </CustomRadioCapsule>
          <bk-button
            class="pl0"
            theme="primary"
            size="small"
            text
            @click="viewPermissionModel"
          >
            {{ $t('查看权限模型') }}
          </bk-button>
        </div>
        <user
          v-model="searchValues"
          style="width: 300px"
          :multiple="true"
          :placeholder="$t('请输入用户名')"
          :empty-text="$t('无匹配人员')"
          @change="handleSearch"
        />
      </div>
      <div class="content-wrapper card-style">
        <bk-table
          :data="paginatedData"
          size="small"
          :pagination="pagination"
          @page-change="pageChange"
          @page-limit-change="limitChange"
          v-bkloading="{ isLoading: isTableLoading, zIndex: 10 }"
        >
          <div slot="empty">
            <table-empty
              :keyword="tableEmptyConf.keyword"
              :abnormal="tableEmptyConf.isAbnormal"
              @reacquire="fetchMemberList"
              @clear-filter="clearFilterKey"
            />
          </div>
          <bk-table-column
            :label="`${$t('用户')} ID`"
            :width="160"
            v-if="platformFeature.MULTI_TENANT_MODE"
          >
            <template #default="{ row }">
              <span>{{ row.user.username }}</span>
            </template>
          </bk-table-column>
          <bk-table-column
            :label="$t('用户名')"
            :render-header="$renderHeader"
          >
            <template slot-scope="{ row }">
              <div v-bk-overflow-tips>
                <span
                  v-if="row.user.avatar"
                  class="user-photo"
                >
                  <img :src="row.user.avatar" />
                </span>
                <bk-user-display-name
                  :user-id="row.user.username"
                  v-if="platformFeature.MULTI_TENANT_MODE"
                ></bk-user-display-name>
                <span v-else>{{ row.user.username }}</span>
              </div>
            </template>
          </bk-table-column>
          <bk-table-column
            :label="$t('角色')"
            :width="220"
            :show-overflow-tooltip="true"
          >
            <template #default="{ row }">
              <span>{{ row.displayRoles }}</span>
            </template>
          </bk-table-column>
          <bk-table-column
            :label="$t('权限描述')"
            min-width="170"
            :show-overflow-tooltip="true"
          >
            <template #default="{ row }">{{ getExactPermissionDescription(row.roles) }}</template>
          </bk-table-column>
          <bk-table-column
            :label="$t('操作')"
            width="220"
          >
            <template #default="props">
              <!-- 平台管理 -->
              <template v-if="isPlatformManage">
                <bk-button
                  text
                  class="mr8"
                  @click="showMemberSideslider(props.row)"
                >
                  {{ $t('更换角色') }}
                </bk-button>
                <bk-button
                  text
                  class="mr8"
                  @click="delMember(props.row.user.username, props.row.user.id)"
                >
                  {{ $t('删除成员') }}
                </bk-button>
              </template>
              <template v-else>
                <bk-button
                  v-if="canManageMe(props.row)"
                  text
                  class="mr8"
                  @click="leaveApp(props.row.user.id, props.row.user.username)"
                >
                  {{ $t('退出应用') }}
                </bk-button>
                <bk-button
                  v-if="canChangeMembers()"
                  text
                  class="mr8"
                  @click="showMemberSideslider(props.row)"
                >
                  {{ $t('更换角色') }}
                </bk-button>
                <bk-button
                  v-if="canManageMembers(props.row)"
                  text
                  class="mr8"
                  @click="delMember(props.row.user.username, props.row.user.id)"
                >
                  {{ $t('删除成员') }}
                </bk-button>
              </template>
            </template>
          </bk-table-column>
        </bk-table>
      </div>
    </paas-content-loader>

    <!-- 新增、更改侧栏 -->
    <MembersSideslider
      :show.sync="membersSidesliderConfig.visiable"
      :data="membersSidesliderConfig.row"
      :config="membersSidesliderConfig"
      :title="membersSidesliderConfig.titleMap[membersSidesliderConfig.type]"
      @confirm="handleSidesliderConfirm"
    />

    <bk-dialog
      v-model="removeUserDialog.visiable"
      width="540"
      :title="`${$t('删除成员')} ${selectedMember.name}`"
      :theme="'primary'"
      :mask-close="false"
      header-position="left"
      :loading="removeUserDialog.isLoading"
      @confirm="delSave"
      @cancel="closeDelModal"
    >
      <div
        slot="header"
        class="del-dialog-header"
        v-bk-overflow-tips
      >
        <span>{{ $t('删除成员') }}</span>
        &nbsp;
        <bk-user-display-name
          :user-id="selectedMember.name"
          v-if="platformFeature.MULTI_TENANT_MODE"
        ></bk-user-display-name>
        <span v-else>{{ selectedMember.name }}</span>
      </div>
      <div>
        {{ $t('用户') }}
        <bk-user-display-name
          :user-id="selectedMember.name"
          v-if="platformFeature.MULTI_TENANT_MODE"
        ></bk-user-display-name>
        <span v-else>{{ selectedMember.name }}</span>
        {{ $t('将失去此应用的对应权限，是否确定删除？') }}
      </div>
    </bk-dialog>

    <bk-dialog
      v-model="leaveAppDialog.visiable"
      width="540"
      :title="$t('退出应用')"
      :theme="'primary'"
      :mask-close="false"
      header-position="left"
      :loading="leaveAppDialog.isLoading"
      @confirm="leaveSave"
      @cancel="closeLeaveApp"
    >
      <div>
        {{ $t('退出并放弃此应用的对应权限，是否确定？') }}
      </div>
    </bk-dialog>
  </div>
</template>

<script>
import auth from '@/auth';
import appBaseMixin from '@/mixins/app-base-mixin';
import user from '@/components/user';
import CustomRadioCapsule from '@/components/custom-radio-capsule';
import { mapState } from 'vuex';
import { paginationFun } from '@/common/utils';
import MembersSideslider from './members-sideslider.vue';

const ROLE_MAPPING = {
  administrator: '管理员',
  developer: '开发者',
  operator: '运营者',
};

const ROLE_ID_TO_NAME_MAPPING = {
  2: 'administrator',
  3: 'developer',
  4: 'operator',
};

export default {
  components: {
    user,
    CustomRadioCapsule,
    MembersSideslider,
  },
  mixins: [appBaseMixin],
  data() {
    return {
      currentUser: auth.getCurrentUser().username,
      loading: true,
      memberList: [],
      filteredData: [],
      roleName: 'administrator',
      selectedMember: {
        id: 0,
        name: '',
      },
      leaveAppDialog: {
        visiable: false,
        isLoading: false,
      },
      removeUserDialog: {
        visiable: false,
        isLoading: false,
      },
      permissionNoticeDialog: {
        visiable: false,
        isLoading: false,
      },
      pagination: {
        current: 1,
        count: 0,
        limit: 10,
      },
      enableToAddRole: false,
      tableEmptyConf: {
        keyword: '',
        isAbnormal: false,
      },
      // 多租户人员搜索
      searchValues: [],
      isTableLoading: false,
      selectedRole: 'all',
      filterList: [
        { id: 0, name: 'all', label: this.$t('全部成员'), count: 0 },
        { id: 2, name: 'administrator', label: this.$t('管理员'), count: 0 },
        { id: 3, name: 'developer', label: this.$t('开发者'), count: 0 },
        { id: 4, name: 'operator', label: this.$t('运营者'), count: 0 },
      ],
      membersSidesliderConfig: {
        visiable: false,
        loading: false,
        row: {},
        type: 'add',
        titleMap: {
          add: this.$t('新增成员'),
          edit: this.$t('更换角色'),
          view: this.$t('权限模型'),
        },
      },
    };
  },
  computed: {
    ...mapState(['platformFeature']),
    // 分页数据
    paginatedData() {
      const { pageData } = paginationFun(this.filteredData, this.pagination.current, this.pagination.limit);
      return pageData;
    },
    contentClass() {
      return this.isPlatformManage ? [] : ['app-container', 'middle', 'role-container'];
    },
    // 是否为平台管理
    isPlatformManage() {
      return this.$route.path.includes('/plat-mgt');
    },
    appCode() {
      if (this.isPlatformManage) {
        return this.$route.params.code;
      }
      return this.$route.params.id;
    },
  },
  watch: {
    $route() {
      this.init();
    },
  },
  created() {
    this.init();
  },
  methods: {
    // 页码变化
    pageChange(page) {
      this.pagination.current = page;
    },
    // 页容量变化
    limitChange(currentLimit) {
      this.pagination.limit = currentLimit;
      this.pagination.current = 1;
    },

    init() {
      this.loading = !this.isPlatformManage;
      if (this.isPlatformManage) {
        this.getPlatformMemberList();
        // 平台管理默认为管理员
        this.enableToAddRole = true;
      } else {
        // 判断当前应用是否为管理员
        this.enableToAddRole = this.curAppInfo && this.curAppInfo.role.name === 'administrator';
        this.fetchMemberList();
      }
    },

    // 获取成员列表
    async fetchMemberList() {
      await this.fetchAndProcessMemberList('member/getMemberList', this.appCode);
    },

    // 获取平台管理成员列表
    async getPlatformMemberList() {
      await this.fetchAndProcessMemberList('tenantOperations/getMembers', this.appCode);
    },

    // 获取成员列表的通用方法
    async fetchAndProcessMemberList(dispatchAction, appCode) {
      this.isTableLoading = true;
      try {
        const res = await this.$store.dispatch(dispatchAction, { appCode });
        const results = this.isPlatformManage ? res : res.results;
        this.memberList = this.processMembers(results);
        this.filteredData = [...this.memberList]; // 过滤数据
        this.pagination.count = results.length;
        this.updateFilterCounts();
        this.updateTableEmptyConfig();
        this.tableEmptyConf.isAbnormal = false;
      } catch (e) {
        this.tableEmptyConf.isAbnormal = true;
        this.catchErrorHandler(e);
      } finally {
        this.loading = false;
        this.isTableLoading = false;
      }
    },

    // 处理成员数据
    processMembers(members) {
      return members.map((user) => {
        const translatedRoles = user.roles.map((role) => this.$t(ROLE_MAPPING[role.name]));
        return {
          ...user,
          displayRoles: translatedRoles.join('，'), // 角色中文显示
        };
      });
    },

    // 更新 filterList 的 count
    updateFilterCounts() {
      // 初始化计数器 {all: 0, administrator: 0, developer: 0, operator: 0}
      const roleCounts = this.filterList.reduce((acc, item) => {
        acc[item.name] = 0;
        return acc;
      }, {});
      // 统计各角色数量
      this.memberList.forEach((member) => {
        roleCounts.all++;
        member.roles.forEach((role) => {
          switch (role.id) {
            case 2:
              roleCounts.administrator++;
              break;
            case 3:
              roleCounts.developer++;
              break;
            case 4:
              roleCounts.operator++;
              break;
          }
        });
      });
      this.filterList = this.filterList.map((item) => ({
        ...item,
        count: roleCounts[item.name],
      }));
    },

    /**
     * 新增成员
     * @parmas 新增成员请求参数
     */
    async addMember(parmas) {
      this.toggleMemberSidesliderLoading(true);
      try {
        const dispatchName = this.isPlatformManage ? 'tenantOperations/addMember' : 'member/addMember';
        await this.$store.dispatch(dispatchName, {
          appCode: this.appCode,
          postParams: parmas,
        });
        this.toggleMemberSideslider(false);
        this.isPlatformManage ? this.getPlatformMemberList() : this.fetchMemberList();
        this.$paasMessage({
          theme: 'success',
          message: this.$t('新增成员成功！'),
        });
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: `${this.$t('添加用户角色失败：')} ${e.detail}`,
        });
      } finally {
        this.toggleMemberSidesliderLoading(false);
      }
    },

    // 退出应用弹窗
    leaveApp(delMemberID, delMemberName) {
      this.selectedMember.id = delMemberID;
      this.selectedMember.name = delMemberName;
      this.leaveAppDialog.visiable = true;
    },

    async leaveSave() {
      this.leaveAppDialog.isLoading = true;
      try {
        await this.$store.dispatch('member/quitApplication', { appCode: this.appCode });
        this.closeLeaveApp();
        this.$router.push({
          path: '/',
        });
      } catch (e) {
        this.closeLeaveApp();
        this.$paasMessage({
          theme: 'error',
          message: `${this.$t('退出应用失败：')} ${e.detail}`,
        });
      } finally {
        this.leaveAppDialog.isLoading = false;
      }
    },

    closeLeaveApp() {
      this.leaveAppDialog.visiable = false;
    },

    // 显示更换成员权限侧栏
    showMemberSideslider({ user, roles }) {
      this.selectedMember.id = user.id;
      this.selectedMember.name = user.username;
      this.roleName = roles[0].name;
      this.membersSidesliderConfig.type = 'edit';
      this.membersSidesliderConfig.row = {
        role: roles[0].id,
        user: user.username,
      };
      this.toggleMemberSideslider(true, 'edit');
    },

    /**
     * 更换成员权限
     * @parmas 请求参数
     */
    async updateSave(parmas) {
      this.toggleMemberSidesliderLoading(true);
      try {
        const dispatchName = this.isPlatformManage ? 'tenantOperations/updateRole' : 'member/updateRole';
        await this.$store.dispatch(dispatchName, {
          appCode: this.appCode,
          id: this.selectedMember.id,
          params: parmas,
        });
        this.toggleMemberSideslider(false);
        this.isPlatformManage ? this.getPlatformMemberList() : this.fetchMemberList();
        this.$paasMessage({
          theme: 'success',
          message: this.$t('角色更换成功！'),
        });
        if (this.selectedMember.name === this.currentUser && this.roleName !== 'administrator') {
          this.enableToAddRole = this.isPlatformManage;
        }
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: `${this.$t('角色更换失败：')} ${e.detail}`,
        });
      } finally {
        this.toggleMemberSidesliderLoading(false);
      }
    },

    delMember(delMemberName, delMemberID) {
      this.selectedMember.id = delMemberID;
      this.selectedMember.name = delMemberName;
      this.removeUserDialog.visiable = true;
    },

    /**
     * 删除成员
     */
    async delSave() {
      this.removeUserDialog.isLoading = true;
      try {
        const dispatchName = this.isPlatformManage ? 'tenantOperations/deleteMember' : 'member/deleteRole';
        await this.$store.dispatch(dispatchName, { appCode: this.appCode, id: this.selectedMember.id });
        this.closeDelModal();
        this.$paasMessage({
          theme: 'success',
          message: this.$t('删除成员成功！'),
        });
        this.isPlatformManage ? this.getPlatformMemberList() : this.fetchMemberList();
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: `${this.$t('删除成员失败：')} ${e.detail}`,
        });
      } finally {
        this.removeUserDialog.isLoading = false;
      }
    },

    closeDelModal() {
      this.removeUserDialog.visiable = false;
    },

    canManageMe(roleInfo) {
      if (roleInfo.user.username !== this.currentUser) {
        return false;
      }
      return true;
    },

    canManageMembers(roleInfo) {
      if (roleInfo.user.username === this.currentUser || !this.enableToAddRole) {
        // 不能操作自身角色 || 非管理员不能操作角色管理
        return false;
      }
      return true;
    },

    canChangeMembers() {
      if (!this.enableToAddRole) {
        return false;
      }
      return true;
    },
    // 搜索处理
    handleSearch() {
      const { searchValues, selectedRole } = this;
      // 重置分页
      this.pagination.current = 1;
      // 如果没有搜索值且选择"全部成员"（或未选择），返回全部数据
      if (!searchValues?.length && (!selectedRole || selectedRole === 'all')) {
        this.filteredData = [...this.memberList];
        this.pagination.count = this.filteredData.length;
        this.updateTableEmptyConfig();
        return;
      }
      const searchSet = new Set(searchValues || []);
      this.filteredData = this.memberList.filter((item) => {
        // 1. 检查用户名是否匹配（如果 searchValues 有值）
        const usernameMatch = !searchValues?.length || (item.user?.username && searchSet.has(item.user.username));

        // 2. 检查权限是否匹配（如果 selectedRole 有值且不是 'all'）
        const roleMatch =
          !selectedRole ||
          selectedRole === 'all' ||
          item.roles?.some((role) => {
            switch (selectedRole) {
              case 'administrator':
                return role.id === 2; // 管理员
              case 'developer':
                return role.id === 3; // 开发者
              case 'operator':
                return role.id === 4; // 运营者
              default:
                return false; // 未知角色
            }
          });

        // 同时满足用户名和权限条件
        return usernameMatch && roleMatch;
      });

      // 更新分页和空状态
      this.pagination.count = this.filteredData.length;
      this.updateTableEmptyConfig();
    },
    // 重置过滤、搜索条件
    clearFilterKey() {
      this.searchValues = [];
      this.selectedRole = 'all';
      this.handleSearch();
    },
    updateTableEmptyConfig() {
      if (this.searchValues.length || this.selectedRole !== 'all') {
        this.tableEmptyConf.keyword = 'placeholder';
        return;
      }
      this.tableEmptyConf.keyword = '';
    },
    // 查看权限模型
    viewPermissionModel() {
      this.toggleMemberSideslider(true, 'view');
    },
    // 切换tab过滤
    handlerFilterChange(data) {
      const { name } = data;
      this.selectedRole = name;
      this.handleSearch();
    },
    // 显示/关闭
    toggleMemberSideslider(falg, type = 'add') {
      this.membersSidesliderConfig.visiable = falg;
      this.membersSidesliderConfig.type = type;
    },
    // 开启/关闭成员管理侧栏
    toggleMemberSidesliderLoading(falg) {
      this.membersSidesliderConfig.loading = falg;
    },

    // 格式多租户成员数据结构
    formatPlatformParams(data) {
      return data.map(({ application, ...rest }) => rest);
    },

    // 侧栏确认事件处理
    handleSidesliderConfirm(parmas, roleId) {
      if (this.membersSidesliderConfig.type === 'add') {
        const platformParmas = this.formatPlatformParams(parmas);
        this.addMember(this.isPlatformManage ? platformParmas : parmas);
      } else {
        const platformParmas = {
          role: {
            id: roleId,
          },
        };
        this.updateSave(this.isPlatformManage ? platformParmas : parmas);
      }
    },
    /**
     * 获取精确权限描述（严格匹配业务需求）
     * @param roles 用户角色数组
     * @returns 精确匹配的权限描述文本
     */
    getExactPermissionDescription(roles = []) {
      const hasRole = (id) => roles.some((role) => role.id === id);
      // 管理员
      if (hasRole(2)) {
        return this.$t('拥有应用全部权限');
      }
      // 开发者+运营者组合（需同时存在）
      if (hasRole(3) && hasRole(4)) {
        return this.$t('拥有开发（部署、日志、配置、云API）、运营（应用访问权限、应用市场信息）等权限');
      }
      // 开发者
      if (hasRole(3)) {
        return this.$t('拥有开发相关的权限（部署、日志、配置、云API），但无法管理应用访问权限和应用成员');
      }
      // 运营者
      if (hasRole(4)) {
        return this.$t('仅可修改应用名称/市场信息、管理应用访问权限、查看访问统计数据和告警记录');
      }
    },
  },
};
</script>

<style lang="scss" scoped>
.role-container {
  width: calc(100% - 48px);
  margin: 16px auto 30px;
  padding-top: 15px;
}
.content-wrapper {
  margin-top: 16px;
  padding: 16px;
  background: #fff;
}
.user-photo {
  margin: 5px 8px 5px 0;
  display: inline-block;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  overflow: hidden;
  border: solid 1px #eaeaea;
  vertical-align: middle;

  img {
    width: 100%;
    height: 100%;
  }
}

.user-name {
  display: inline-block;
  padding-left: 10px;
  font-size: 14px;
  color: #333;
  vertical-align: middle;
}

.ps-pr {
  padding-right: 15px;
  color: #999;
}

.role-label {
  display: inline-block;
  background: #fafafa;
  font-size: 12px;
  border: 1px solid;
  vertical-align: middle;
  box-sizing: border-box;
  overflow: hidden;
  white-space: nowrap;
  padding: 0 8px;
  height: 21px;
  line-height: 19px;
  border-radius: 21px;
  margin: 0px 8px;
  border-color: #3c96ff;
  color: #3c96ff;
}

.right-main .header {
  display: flex;
  justify-content: space-between;
  .mr12 {
    margin-right: 12px;
  }
}

.del-dialog-header {
  color: #313238;
  font-size: 24px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
