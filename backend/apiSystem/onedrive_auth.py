import os, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'apiSystem.settings')
sys.path.insert(0, '/app/apiSystem')
sys.path.insert(0, '/app')
import django
django.setup()
from apps.core.cloud_storage.models import CloudStorageAccount
from apps.core.cloud_storage.onedrive_provider import OAuthTokenManager

acc = CloudStorageAccount.objects.filter(storage_type="onedrive").first()
if not acc:
    print("❌ 未找到 OneDrive 账号"); sys.exit(1)
if not acc.onedrive_client_id:
    print("❌ Client ID 为空"); sys.exit(1)

print("="*50)
print("📋 获取设备码...")
result = OAuthTokenManager.start_device_code_flow(acc)
print(f"✅ 设备码已生成！")
print()
print(f"🔗 请访问: {result['verification_uri']}")
print(f"🔑 设备码: {result['user_code']}")
print()
input("👉 完成授权后按 Enter 继续...")

print("📋 正在轮询获取 token...")
manager = OAuthTokenManager(acc)
try:
    token = manager.complete_device_code_flow(result["device_code"])
    print(f"✅ 授权成功！Token: {token[:30]}...")
except Exception as e:
    print(f"❌ 授权失败: {e}")
    sys.exit(1)

acc.refresh_from_db()
print(f"Refresh Token: {'✅ 存在' if acc.onedrive_refresh_token else '❌ 不存在'}")
if acc.onedrive_refresh_token:
    print("🎉 刷新 Admin 页面，即可看到「已授权」")
