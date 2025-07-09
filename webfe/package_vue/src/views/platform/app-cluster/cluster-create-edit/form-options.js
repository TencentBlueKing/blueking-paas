import store from '@/store';
import i18n from '@/language/i18n.js';

// 必填规则
const requiredRule = [
  {
    required: true,
    message: i18n.t('必填项'),
    trigger: 'blur',
  },
];

const infoOptions = [
  {
    label: '集群名称',
    type: 'input',
    property: 'name',
    maxlength: 32,
    required: true,
    rules: [
      ...requiredRule,
      {
        regex: /^[A-Za-z0-9-]{3,32}$/,
        message: i18n.t('集群名称，为 3 到 32 个字符，只能包含大小写字母、数字和连接符（-）'),
        trigger: 'blur',
      },
    ],
  },
  {
    label: '集群描述',
    type: 'textarea',
    property: 'description',
    maxlength: 128,
    required: true,
    rules: [...requiredRule],
  },
];

// 容器日志目录、集群访问入口 IP
const commonOptions = [
  {
    label: '容器日志目录',
    type: 'input',
    property: 'container_log_dir',
    required: true,
    tips: 'docker 默认 /var/lib/docker/containers; containerd 默认 /var/lib/containerd.',
    rules: [...requiredRule],
  },
  {
    label: '集群访问入口 IP',
    type: 'input',
    property: 'access_entry_ip',
    tips: '用于指引用户配置独立域名的解析，如果集群使用云厂商的 clb 做流量控制，这里需要填写对应的 vip',
  },
];

const clusterSource = [
  {
    label: '集群来源',
    type: 'radio',
    property: 'cluster_source',
    required: true,
    radios: [
      { value: 'bcs', label: 'BCS 集群' },
      { value: 'native_k8s', label: 'K8S 集群（不推荐，无法使用访问控制台等功能）' },
    ],
  },
];

const apiAddressType = [
  {
    label: '集群 API 地址类型',
    type: 'radio',
    property: 'api_address_type',
    required: true,
    radios: [
      {
        value: 'bcs_gateway',
        label: 'BCS 网关',
        tip: '通过 BCS 提供的网关操作集群，格式如：https://bcs-api.bk.example.com/clusters/BCS-K8S-00000/',
        disabledFn(val) {
          return val === 'native_k8s';
        },
      },
      {
        value: 'custom',
        label: '自定义',
        tip: '可通过 IP + Port 或 Service 名称访问，如：https://127.0.0.1:8443，https://kubernetes.default.svc.cluster.local 等',
      },
    ],
  },
];

const clusterToken = [
  {
    label: '集群 Token',
    type: 'password',
    property: 'token',
    required: true,
    tips: '如 Master 节点 /root/.kube/config 文件中 admin 用户 user.token 的值',
    // tipBtn: '集群配置说明',
    rules: [...requiredRule],
  },
];

// BCS集群
export const bcsOptions = [
  ...infoOptions,
  ...clusterSource,
  {
    label: '项目',
    type: 'select',
    property: 'bcs_project_id',
    editProperty: 'bcs_project_name',
    required: true,
    searchable: true,
    rules: [...requiredRule],
    source: {
      // 通过接口获取数据
      api: () => {
        return store.dispatch('tenant/getBcsProjects');
      },
    },
  },
  {
    label: 'BCS 集群',
    type: 'select',
    property: 'bcs_cluster_id',
    editProperty: 'bcs_cluster_name',
    required: true,
    searchable: true,
    tips: '为方便接入和管理，请先将集群导入至 BCS',
    rules: [...requiredRule],
    source: {
      // BCS集群 依赖 项目
      dependency: 'bcs_project_id',
      api: async (arg) => {
        if (!arg) return [];
        try {
          const res = await store.dispatch('tenant/getBcsClusters', {
            projectId: arg,
          });
          return res.map((item) => {
            return {
              ...item,
              name: `${item.name}（${item.id}）`,
            };
          });
        } catch (e) {
          Promise.reject(e);
        }
      },
    },
  },
  {
    label: '业务',
    type: 'input',
    property: 'bk_biz_id',
    editProperty: 'bk_biz_name',
    required: true,
    disabled: true,
  },
  ...apiAddressType,
  {
    label: '集群 Server',
    type: ['input', 'arr-input'],
    property: 'api_servers',
    disabled: true,
    required: true,
  },
  ...clusterToken,
  ...commonOptions,
];

// K8S集群-token
export const tokenOptions = [...clusterToken];

// K8S集群-证书
export const certOptions = [
  {
    label: '证书认证机构',
    type: 'textarea',
    property: 'ca',
    maxlength: 4096,
    required: true,
    rules: [...requiredRule],
  },
  {
    label: '客户端证书',
    type: 'textarea',
    property: 'cert',
    maxlength: 4096,
    required: true,
    rules: [...requiredRule],
  },
  {
    label: '客户端密钥',
    type: 'textarea',
    property: 'key',
    maxlength: 4096,
    required: true,
    rules: [...requiredRule],
  },
];

// K8S集群
export const k8sOptions = [
  ...infoOptions,
  ...clusterSource,
  {
    label: '集群认证方式',
    type: 'radio',
    property: 'auth_type',
    required: true,
    radios: [
      { value: 'token', label: 'Token' },
      { value: 'cert', label: '证书' },
    ],
  },
  ...apiAddressType,
  // k8s默认为自定义
  {
    label: 'APIServers',
    type: 'arr-input',
    property: 'api_servers_list',
    required: true,
  },
  ...commonOptions,
];

export const elasticSearchOptions = [
  {
    label: '协议',
    type: 'select',
    property: 'scheme',
    required: true,
    rules: [...requiredRule],
    source: {
      api: () => {
        return [
          { id: 'http', name: 'HTTP' },
          { id: 'https', name: 'HTTPS' },
        ];
      },
    },
  },
  {
    label: '主机',
    type: 'input',
    property: 'host',
    required: true,
    rules: [...requiredRule],
  },
  {
    label: '端口',
    type: 'input',
    property: 'port',
    required: true,
    rules: [...requiredRule],
  },
  {
    label: '用户名',
    type: 'input',
    property: 'username',
    required: true,
    rules: [...requiredRule],
  },
  {
    label: '密码',
    type: 'password',
    property: 'password',
    required: true,
    rules: [...requiredRule],
  },
];

export const availableTenantsOptions = [
  {
    label: '可用租户',
    type: 'select',
    property: 'available_tenant_ids',
    multiple: true,
    'display-tag': true,
    required: true,
    rules: [...requiredRule],
    source: {
      api: () => {
        return store.dispatch('tenant/getTenants');
      },
    },
  },
];

// 组件配置信息
export const componentConfigOptions = [
  {
    label: '命名空间',
    type: 'input',
    property: 'component_preferred_namespace',
    required: true,
    tips: '为方便管理，后续组件都建议安装在这个命名空间下',
    rules: [...requiredRule],
  },
  {
    label: '镜像仓库',
    type: 'input',
    property: 'component_image_registry',
    required: true,
    tips: '如使用自定义的镜像仓库，请确认相关镜像已经推送到该仓库',
    rules: [...requiredRule],
  },
  {
    label: '应用访问类型',
    type: 'radio',
    property: 'app_address_type',
    required: true,
    radios: [
      {
        value: 'subpath',
        label: '子路径',
        tip: '集群上所有应用共用一个域名，应用的访问地址形如：apps.example.com/appid',
      },
      {
        value: 'subdomain',
        label: '子域名',
        tip: '需要给应用申请一个泛域名（如：*.apps.example.com），应用的访问地址形式如：appid.apps.example.com',
      },
    ],
  },
  {
    label: '应用域名',
    type: 'arr-input',
    property: 'app_domains',
    required: true,
    tips: '应用域名需要配置解析到集群的出口 IP',
  },
];

// 镜像仓库配置信息
export const mirrorRepositoryOptions = [
  {
    label: '镜像仓库域名',
    type: 'input',
    property: 'host',
    required: true,
    placeholder: '请输入镜像仓库的域名，如：mirrors.tencent.com',
    rules: [...requiredRule],
  },
  {
    label: '命名空间',
    type: 'input',
    property: 'namespace',
    required: true,
    placeholder: '请输入命名空间，如：bkpaas/docker',
    rules: [...requiredRule],
  },
  {
    label: '用户名',
    type: 'input',
    property: 'username',
    required: true,
    rules: [...requiredRule],
  },
  {
    label: '密码',
    type: 'password',
    property: 'password',
    required: true,
    rules: [...requiredRule],
  },
  {
    label: '跳过证书验证',
    type: 'switcher',
    property: 'skip_tls_verify',
    required: true,
    rules: [...requiredRule],
    tips: '如果镜像仓库的域名未配 HTTPS 证书时，需要开启该选项',
  },
];
