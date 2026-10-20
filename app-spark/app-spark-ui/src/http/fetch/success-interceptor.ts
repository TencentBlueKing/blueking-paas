import type { IFetchConfig } from './index';
import RequestError from './request-error';

const hasNoBody = (response: Response) => (
  response.status === 204
  || response.status === 205
  || response.headers.get('content-length') === '0'
);

// 请求成功执行拦截器
export default async (response: Response, config: IFetchConfig) => {
  // 删除这类接口常以 204 或空 body 表示成功。按 JSON 去读会直接抛解析错误。
  if (hasNoBody(response)) {
    if (response.ok) return null;
    throw new RequestError(response.status, response.statusText || '系统错误', null);
  }

  let body: any;
  try {
    body = await response[config.responseType]();
  } catch (error) {
    if (response.ok) return null;
    throw error;
  }

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
