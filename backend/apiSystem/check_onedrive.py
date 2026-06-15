import os, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'apiSystem.settings')
sys.path.insert(0, '/app/apiSystem')
sys.path.insert(0, '/app')

import django
django.setup()

from apps.core.cloud_storage.models import CloudStorageAccount

acc = CloudStorageAccount.objects.filter(storage_type="onedrive").first()
if not acc:
    print("❌ 未找到 OneDrive 账号")
    sys.exit(1)

print("=== 账号基本信息 ===")
print("ID:", acc.id)
print("名称:", acc.name)
print("Client ID:", acc.onedrive_client_id[:20] if acc.onedrive_client_id else "空")
print("Refresh Token 是否存在:", bool(acc.onedrive_refresh_token))
print("Pending Device Code:", (acc.onedrive_pending_device_code or "")[:20] if acc.onedrive_pending_device_code else "空")
print("Pending Expires:", acc.onedrive_pending_expires_at)
print("Token Expires:", acc.onedrive_token_expires_at)
print()
print("=== 检查数据库表字段 ===")
cols = [f.name for f in acc._meta.fields]
for c in ["onedrive_pending_device_code","onedrive_pending_expires_at","onedrive_refresh_token","onedrive_access_token"]:
    ok = "✅ 存在" if c in cols else "❌ 不存在"
    print(f"  字段 [{c}]: {ok}")
