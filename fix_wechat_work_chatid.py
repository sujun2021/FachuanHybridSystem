#!/usr/bin/env python3
import re

# 读取文件
with open('/root/podman/FachuanHybridSystem/backend/apps/automation/services/chat/wechat_work_provider.py', 'r') as f:
    content = f.read()

# 修改 chatid 生成逻辑
old_code = '            payload: dict[str, Any] = {\n                "name": chat_name,\n                "owner": effective_owner_id,\n                "userlist": [effective_owner_id],\n                "chatid": f"case_{chat_name[:50]}",\n            }'

new_code = '''            payload: dict[str, Any] = {
                "name": chat_name,
                "owner": effective_owner_id,
                "userlist": [effective_owner_id],
            }'''

if old_code in content:
    content = content.replace(old_code, new_code)
    with open('/root/podman/FachuanHybridSystem/backend/apps/automation/services/chat/wechat_work_provider.py', 'w') as f:
        f.write(content)
    print("✅ 已成功移除 chatid 指定")
else:
    print("⚠️ 未找到需要修改的代码")
