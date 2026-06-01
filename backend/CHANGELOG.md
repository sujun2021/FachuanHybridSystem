# Changelog

## 26.50.10

### 后端

#### 修复
- 移除登录页面外部 CDN 依赖（Google Fonts、jsdelivr），改用本地静态资源，解决国内网络 ERR_CONNECTION_CLOSED 错误
- 修复 Lawyer email 字段空字符串导致 PostgreSQL 唯一约束冲突，将空字符串转为 NULL

## 26.48.11

### 后端

#### 新功能
- 接入 kimi26 (vLLM) 模型，默认 base_url 指向 `http://116.196.92.175:8001/v1`
- 初始化默认配置新增 `OPENAI_COMPATIBLE_BASE_URL`、`OPENAI_COMPATIBLE_DEFAULT_MODEL` 种子配置项
- kimi26 思考模式通过 `chat_template_kwargs: {"thinking": False}` 自动关闭

#### 修复
- `_build_extra_body()` 改为使用实际请求模型判断，修复显式传 `model="kimi26"` 时思考模式未关闭的 bug
- 模型列表服务跳过未启用后端的查询，避免无效的 SiliconFlow 401 报错
- 添加 `beautifulsoup4` 依赖，修复 MCP server web_search 工具启动报错

#### 移除
- 彻底移除 Moonshot 后端（`MoonshotBackend` 类、`get_moonshot_*()` 方法、registry/router/service 中的 moonshot 条目）
- `DEFAULT_OPENAI_COMPATIBLE_MODEL` 从 `moonshot-v1-8k` 改为 `kimi26`
- `DEFAULT_OPENAI_COMPATIBLE_BASE_URL` 从 `https://api.moonshot.cn/v1` 改为 kimi26 vLLM 地址

#### 依赖变更
- 新增 `beautifulsoup4>=4.14.3`
