/**
 * 路由预加载工具
 * 在用户 hover 侧边栏链接时提前加载页面 chunk，实现点击即打开
 */

const prefetched = new Set<string>()

export function prefetchRoute(key: string, importFn: () => Promise<unknown>) {
  if (prefetched.has(key)) return
  prefetched.add(key)
  importFn()
}
