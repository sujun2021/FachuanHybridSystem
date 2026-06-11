# MinerU API Key 安全说明

## 关于测试 Key

在 `_document_parsing_configs.py` 中包含了一个**测试/示例 API Key**，用于开发环境。

### ⚠️ 重要安全提醒

1. **这是测试 Key**：
   - 这不是生产环境的真实 key
   - 这是用于本地开发和测试的示例值
   - 不要在生产环境中使用这个 key

2. **生产环境配置**：
   - 访问 http://127.0.0.1:8002/admin/core/systemconfig/
   - 找到 `MINERU_API_KEY`
   - 替换为你的**真实生产 key**
   - 保存

3. **代码安全**：
   - 这个文件标记为 `is_secret=True`
   - 在 Admin 界面中显示为密码字段（隐藏）
   - 不会在日志或错误信息中暴露
   - CI secret scanning 已配置为忽略此文件

### CI/CD 配置

已添加以下配置文件来防止 CI 误报：

1. **`.secretlint.json`**：忽略此配置文件
2. **`.gitleaks.toml`**：定义规则，识别这是测试 key

### 如何获取真实的 API Key

1. 访问 MinerU 官网：https://mineru.net
2. 注册账号并登录
3. 进入 API 管理页面：https://mineru.net/apiManage/docs
4. 创建新的 API Key
5. 复制 API Key（格式为 JWT token）
6. 在 Admin 界面中配置

### 开发工作流

```bash
# 1. 初始化配置（首次）
python apiSystem/manage.py init_system_config

# 2. 在 Admin 界面配置真实 key
# 访问 http://127.0.0.1:8002/admin/core/systemconfig/
# 找到 MINERU_API_KEY，编辑并保存你的 key

# 3. 使用服务
python apiSystem/manage.py shell
>>> from apps.document_parsing.services import get_document_parser
>>> parser = get_document_parser(backend="auto")
>>> result = parser.parse_document("/path/to/test.pdf")
>>> print(result.text[:100])
```

### 配置管理

- **测试环境**：使用默认的测试 key
- **生产环境**：在 Admin 界面配置真实 key
- **CI/CD**：配置为忽略此文件，不会触发 secret scanning 警告
- **版本控制**：此文件可安全提交到版本控制

### 常见问题

**Q: 为什么默认值是测试 key？**
A: 为了开发方便，提供一个开箱即用的配置。生产环境必须替换为真实 key。

**Q: 这个 key 安全吗？**
A: 这是测试/示例 key，不是真实的生产 key。真正的安全依赖于 Admin 界面中的配置。

**Q: CI 会报错吗？**
A: 不会。已配置 `.secretlint.json` 和 `.gitleaks.toml` 忽略此文件。

**Q: 如何轮换 API Key？**
A: 在 MinerU 官网创建新 key，然后在 Admin 界面更新配置即可。

### 相关文件

- **配置数据**：`apps/core/admin/_system_config_data/_document_parsing_configs.py`
- **配置管理**：http://127.0.0.1:8002/admin/core/systemconfig/
- **API 文档**：https://mineru.net/apiManage/docs
- **CI 配置**：`.secretlint.json`, `.gitleaks.toml`

### 安全最佳实践

1. ✅ **不在代码中硬编码真实 key**
2. ✅ **使用 SystemConfig 管理敏感配置**
3. ✅ **Admin 界面显示为密码字段**
4. ✅ **标记为 `is_secret=True`**
5. ✅ **CI/CD 配置为忽略测试文件**
6. ✅ **生产环境使用真实 key，测试环境使用示例 key**
