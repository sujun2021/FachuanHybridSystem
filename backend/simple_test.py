import sys
sys.path.insert(0, 'apiSystem')
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'apiSystem.settings')

import django
django.setup()

from apps.cases.models import CasePaymentRecord, PaymentRecordCategory, CaseLogBatch, CaseLog
from django.conf import settings

print("=== 模型测试 ===")
print(f"AUTH_USER_MODEL: {settings.AUTH_USER_MODEL}")
print(f"CasePaymentRecord 字段: {[f.name for f in CasePaymentRecord._meta.fields]}")
print(f"CaseLogBatch 字段: {[f.name for f in CaseLogBatch._meta.fields]}")
print(f"CaseLogBatch has_income_split: {hasattr(CaseLogBatch, 'has_income_split')}")

from apps.cases.services import LogBatchService, PaymentRecordService, ContentSplitService
print("\n=== 服务测试 ===")
print("服务导入成功")

from apps.cases.api import router as cases_router
print("\n=== API路由测试 ===")
routes = [path for path, _, _ in cases_router.urls]
payment_routes = [r for r in routes if 'payment' in r.lower()]
batch_routes = [r for r in routes if 'batch' in r.lower()]
print(f"案件模块路由: {len(routes)} 条")
print(f"收支相关路由: {payment_routes}")
print(f"批量日志路由: {batch_routes}")

print("\n=== 测试完成 ===")
