export interface AuthUser {
  username: string;
}

/** 蓝鲸登录态由平台注入，生成代码通过这里读取，不要自行解析 cookie。 */
export async function getCurrentUser(): Promise<AuthUser | null> {
  return null;
}

export function isAuthenticated(): boolean {
  return false;
}
