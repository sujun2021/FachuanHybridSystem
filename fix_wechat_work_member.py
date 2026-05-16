#!/usr/bin/env python3

# 读取文件
with open('/root/podman/FachuanHybridSystem/backend/apps/automation/services/chat/wechat_work_provider.py', 'r') as f:
    content = f.read()

# 修改 payload 部分
old_code = '            payload: dict[str, Any] = {\n                "name": chat_name,\n                "owner": effective_owner_id,\n                "userlist": [effective_owner_id],\n            }'

new_code = '''            # 企业微信创建群聊至少需要2个成员
            payload: dict[str, Any] = {
                "name": chat_name,
                "owner": effective_owner_id,
                "userlist": [effective_owner_id, effective_owner_id],
            }'''

if old_code in content:
    content = content.replace(old_code, new_code)
    with open('/root/podman/FachuanHybridSystem/backend/apps/automation/services/chat/wechat_work_provider.py', 'w') as f:
        f.write(content)
    print("✅ 已成功修复群成员问题")
else:
    print("⚠️ 未找到需要修改的代码")
