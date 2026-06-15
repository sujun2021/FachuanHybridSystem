import os, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'apiSystem.settings')
sys.path.insert(0, '/app/apiSystem')
sys.path.insert(0, '/app')
import django
django.setup()

from apps.core.cloud_storage.factory import create_provider_from_account
from apps.core.cloud_storage.models import CloudStorageAccount

acc = CloudStorageAccount.objects.filter(storage_type="onedrive").first()

# 先看 onedrive_root_path 设置
print(f"onedrive_root_path: '{acc.onedrive_root_path}'")
print()

provider = create_provider_from_account(acc)

# 列出根目录所有文件夹名
items = provider.list_directory("")
dirs = [i for i in items if i.is_dir]
print(f"=== 根目录共 {len(dirs)} 个文件夹 ===")

# 搜索含 work 的文件夹
for d in dirs:
    if "work" in d.name.lower():
        print(f"  📁 {d.name}")

# 检查完全匹配
found = [d.name for d in dirs if d.name.lower() == "worksync"]
if found:
    print(f"\n✅ 找到 'worksync' 文件夹（实际名字: {found[0]}）")
else:
    print(f"\n❌ 没有 'worksync' 文件夹")
    print(f"\n=== 前 20 个文件夹 ===")
    for d in dirs[:20]:
        print(f"  📁 {d.name}")
