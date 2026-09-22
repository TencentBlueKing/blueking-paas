export default class RequestError extends Error {
  // 老协议里是数字（HTTP 状态码，或 body 里的 code），app-spark-api 用的是稳定的业务错误码
  // 字符串（见 @/http/error-codes），所以两种都得容得下。
  public code: number | string;
  public message: string;
  public response: any;
  constructor(code: number | string, message: string, response?: any) {
    super();
    this.code = code;
    this.message = message;
    this.response = response;
  }
}
