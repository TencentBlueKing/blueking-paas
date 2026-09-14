import { deepMerge } from '@/common/util';
import successInterceptor from './success-interceptor';
import errorInterceptor from './error-interceptor';
import RequestError from './request-error';

export interface IFetchConfig extends RequestInit {
  responseType?: 'json' | 'text' | 'arrayBuffer' | 'blob' | 'formData',
  globalError?: boolean
}

type HttpMethod = (url: string, payload?: any, config?: IFetchConfig) => Promise<any>;

interface IHttp {
  get?: HttpMethod;
  post?: HttpMethod;
  put?: HttpMethod;
  delete?: HttpMethod;
  head?: HttpMethod;
  options?: HttpMethod;
  patch?: HttpMethod;
}

// Content-Type
const contentTypeMap = {
  json: 'application/json',
  text: 'text/plain',
  formData: 'multipart/form-data',
};
const methodsWithoutData = ['delete', 'get', 'head', 'options'];
const methodsWithData = ['post', 'put', 'patch'];
const allMethods = [...methodsWithoutData, ...methodsWithData];

// 拼装发送请求配置
const getFetchConfig = (method: string, payload: any, config: IFetchConfig) => {
  // 合并配置
  let fetchConfig: IFetchConfig = deepMerge(
    {
      method: method.toLocaleUpperCase(),
      mode: 'cors',
      cache: 'default',
      credentials: 'include',
      headers: {
        'X-Requested-With': 'fetch',
        'Content-Type': contentTypeMap[config.responseType] || 'application/json',
      },
      redirect: 'follow',
      referrerPolicy: 'no-referrer-when-downgrade',
      responseType: 'json',
      globalError: true,
    },
    config,
  );
  if (methodsWithData.includes(method)) {
    fetchConfig = deepMerge(fetchConfig, { body: JSON.stringify(payload) });
  }
  return fetchConfig;
};

/** 同源 API 地址：origin + SITE_URL + 业务 path，避免调用方二次拼接站点前缀 */
export const resolveApiUrl = (path: string) => {
  if (/^https?:\/\//.test(path)) return path;
  const site = String(window.SITE_URL || '').replace(/\/$/, '');
  const ajax = String(process.env.BK_AJAX_URL_PREFIX || '').replace(/\/$/, '');
  const normalized = path.startsWith('/') ? path : `/${path}`;
  return `${location.origin}${site}${ajax}${normalized}`;
};

// 拼装发送请求 url
const getFetchUrl = (url: string, method: string, payload = {}) => {
  try {
    const urlObject: URL = new URL(resolveApiUrl(url));
    // get 请求需要将参数拼接到url上
    if (methodsWithoutData.includes(method)) {
      Object.keys(payload).forEach((key) => {
        const value = payload[key];
        if (!['', undefined, null].includes(value)) {
          urlObject.searchParams.append(key, value);
        }
      });
    }
    return urlObject.href;
  } catch (error: any) {
    throw new RequestError(-1, error.message);
  }
};

// 在自定义对象 http 上添加各请求方法
const http: IHttp = {};
allMethods.forEach((method) => {
  Object.defineProperty(http, method, {
    get() {
      return async (url: string, payload: any, config: IFetchConfig = {}) => {
        const fetchConfig: IFetchConfig = getFetchConfig(method, payload, config);
        try {
          const fetchUrl = getFetchUrl(url, method, payload);
          const response = await fetch(fetchUrl, fetchConfig);
          return await successInterceptor(response, fetchConfig);
        } catch (err) {
          return errorInterceptor(err, fetchConfig);
        }
      };
    },
  });
});

export default http;
