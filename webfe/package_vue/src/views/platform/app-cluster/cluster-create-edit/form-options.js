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
        rules: [...requiredRule],
    },
    {
        label: '集群描述',
        type: 'textarea',
        property: 'description',
        maxlength: 100,
        required: true,
        rules: [...requiredRule],
    },
];

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
        tips: '用于指引用户配置独立域名的解析，如果集群使用云厂商的 clb 做流量控制，那么这里应当填对应的vip',
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

const clusterToken = [
    {
        label: '集群 Token',
        type: 'input',
        property: 'token',
        required: true,
        tips: '如 Master 节点/root/.kube/config 文件中 admin 用户 user.token 的值',
        tipBtn: '集群配置说明',
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
        required: true,
        rules: [...requiredRule],
        source: {
            // 通过接口获取数据
            api: () => {
                return store.dispatch('tenant/getBcsProjects');
            }
        },
    },
    {
        label: 'BCS 集群',
        type: 'select',
        property: 'bcs_cluster_id',
        required: true,
        tips: '为方便接入和管理，请先将集群导入至 BCS',
        rules: [...requiredRule],
        source: {
            // BCS集群 依赖 项目
            dependency: 'bcs_project_id',
            api: (arg) => {
                return store.dispatch('tenant/getBcsClusters', {
                    projectId: arg
                });
            }
        },
    },
    {
        label: '业务',
        type: 'input',
        property: 'bk_biz_id',
        required: true,
        disabled: true,
    },
    {
        label: '集群 Server',
        type: 'input',
        property: 'api_servers',
        disabled: true,
    },
    ...clusterToken,
    ...commonOptions,
];

// K8S集群-token
export const tokenOptions = [
    ...clusterToken,
];

// K8S集群-证书
export const certOptions = [
    {
        label: '证书认证机构',
        type: 'textarea',
        property: 'ca',
        maxlength: 100,
        required: true,
        rules: [...requiredRule],
    },
    {
        label: '客户端证书',
        type: 'textarea',
        property: 'cert',
        maxlength: 100,
        required: true,
        rules: [...requiredRule],
    },
    {
        label: '客户端密钥',
        type: 'textarea',
        property: 'key',
        maxlength: 100,
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
        ]
    },
    {
        label: 'APIServers',
        type: 'arr-input',
        property: 'api_servers_list',
        maxlength: 100,
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
            }
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
            }
        },
    },
];
