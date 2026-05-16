#!/usr/bin/env python3

# 读取文件
with open('/root/podman/FachuanHybridSystem/backend/apps/automation/services/chat/wechat_work_provider.py', 'r') as f:
    content = f.read()

# 修改 payload 部分
old_code = '            payload: dict[str, Any] = {\n                "name": chat_name,\n                "owner": effective_owner_id,\n                "userlist": [effective_owner_id, effective_owner_id],\n            }'

new_code = '''            # 企业微信创建群聊至少需要2个不同的成员
            secondary_member = self.config.get("SECONDARY_MEMBER_ID", effective_owner_id)
            userlist = [effective_owner_id]
            if secondary_member != effective_owner_id:
                userlist.append(secondary_member)
            else:
                # 如果没有配置第二个成员，使用群主作为第二个成员（允许重复以满足最小人数要求）
                userlist.append(effective_owner_id)
            
            payload: dict[str, Any] = {
                "name": chat_name,
                "owner": effective_owner_id,
                "userlist": userlist,
            }'''

if old_code in content:
    content = content.replace(old_code, new_code)
    with open('/root/podman/FachuanHybridSystem/backend/apps/automation/services/chat/wechat_work_provider.py', 'w') as f:
        f.write(content)
    print("✅ 已成功修复群成员问题")
else:
    print("⚠️ 未找到需要修改的代码")
    # 显示当前 payload 部分
    import re
    match = re.search(r'payload: dict$$str, Any$$ = \{.*?\}', content, re.DOTALL)
    if match:
        print("当前 payload 代码:")
        print(match.group())
