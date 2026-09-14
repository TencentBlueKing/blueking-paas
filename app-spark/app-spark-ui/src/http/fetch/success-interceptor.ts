import type { IFetchConfig } from './index';
import RequestError from './request-error';

// 请求成功执行拦截器
export default async (response: any, config: IFetchConfig) => {
  const body = await response[config.responseType]();
  if (response.ok) {
    // 旧协议：{ code, data, message }，code === 0 为成功
    if (body && typeof body === 'object' && Object.prototype.hasOwnProperty.call(body, 'code')) {
      if (body.code === 0) {
        return body.data;
      }
      throw new RequestError(body.code, body.message || '系统错误', body.data);
    }
    // 新协议：HTTP 2xx 且 body 即为业务数据
    return body;
  }

  const message = (body && (body.detail || body.message)) || response.statusText || '系统错误';
  throw new RequestError(body?.code ?? response.status ?? -1, message, body);
};
