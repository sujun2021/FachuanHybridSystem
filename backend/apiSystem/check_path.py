import os, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'apiSystem.settings')
sys.path.insert(0, '/app/apiSystem')
sys.path.insert(0, '/app')
import django
django.setup()

from apps.core.cloud_storage.factory import create_provider_from_account
from apps.core.cloud_storage.models import CloudStorageAccount

acc = CloudStorageAccount.objects.filter(storage_type="onedrive").first()
if not acc:
    print("❌ 未找到 OneDrive 账号")
    exit(1)

print("✅ 账号已找到, 正在连接 OneDrive...")
provider = create_provider_from_account(acc)

# 先测试根目录
print("\n=== 测试根目录 ===")
items = provider.list_directory("")
print(f"  根目录文件/文件夹数: {len(items)}")
for item in items[:8]:
    print(f"  {'📁' if item.is_dir else '📄'} {item.name}")

# 分级检查绑定路径
path = "/worksync/工作文件夹【微盘的补充】/02诉讼/【诉讼】纳雍天然气vs 黔湖 红枫 4811-7195"
print(f"\n=== 分级检查路径 ===")
parts = path.strip("/").split("/")
current = ""
for i, p in enumerate(parts):
    current = current + "/" + p if current else p
    try:
        ok = provider.exists("/" + current)
        print(f"  [{i+1}] /{p} -> {'✅ 存在' if ok else '❌ 不存在'}")
    except Exception as e:
        print(f"  [{i+1}] /{p} -> ❌ 出错: {e}")
        break

print("\n✅ 检查完成")
