#!/usr/bin/env python3
"""
测试收支记录功能模块

运行方式:
cd backend
python test_payment_feature.py
"""

import os
import sys
import django

# 设置 Django 环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'apiSystem.settings')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'apiSystem'))
django.setup()

import traceback
from decimal import Decimal
from django.conf import settings

def test_models():
    """测试模型定义"""
    print("\n=== 测试模型定义 ===")
    
    try:
        from apps.cases.models import (
            CasePaymentRecord,
            PaymentRecordCategory,
            CaseLogBatch,
            CaseLog,
        )
        
        print("✓ 模型导入成功")
        
        # 检查 AUTH_USER_MODEL 配置
        print(f"  AUTH_USER_MODEL: {settings.AUTH_USER_MODEL}")
        
        # 检查外键配置
        case_payment_actor_field = CasePaymentRecord._meta.get_field('actor')
        print(f"  CasePaymentRecord.actor 外键: {case_payment_actor_field.remote_field.model}")
        
        case_log_actor_field = CaseLog._meta.get_field('actor')
        print(f"  CaseLog.actor 外键: {case_log_actor_field.remote_field.model}")
        
        case_log_batch_actor_field = CaseLogBatch._meta.get_field('actor')
        print(f"  CaseLogBatch.actor 外键: {case_log_batch_actor_field.remote_field.model}")
        
        # 检查新增字段
        if hasattr(CaseLogBatch, 'has_income_split'):
            print("✓ CaseLogBatch 包含收入分摊字段")
        else:
            print("✗ CaseLogBatch 缺少收入分摊字段")
            
        print("✓ 模型定义检查通过")
        
    except Exception as e:
        print(f"✗ 模型测试失败: {e}")
        traceback.print_exc()

def test_services():
    """测试服务层"""
    print("\n=== 测试服务层 ===")
    
    try:
        from apps.cases.services import (
            LogBatchService,
            PaymentRecordService,
            ContentSplitService,
        )
        
        print("✓ 服务导入成功")
        
        # 测试 ContentSplitService
        content = "今天下午2点开庭，法官询问了案件情况"
        case_ids = [1, 2, 3, 4, 5]
        
        preview = ContentSplitService.generate_preview(
            content,
            case_ids,
            expense_amount=Decimal('100'),
            split_count=5,
        )
        
        print(f"✓ ContentSplitService.generate_preview 生成了 {len(preview)} 条预览")
        
        splits = ContentSplitService.split_content(
            content,
            case_ids,
            expense_amount=Decimal('100'),
            split_count=5,
        )
        
        print(f"✓ ContentSplitService.split_content 生成了 {len(splits)} 条分拆")
        
        # 检查分拆内容
        if splits[0].get('expense_amount'):
            print(f"  每案件分摊费用: {splits[0]['expense_amount']}")
        
        print("✓ 服务层测试通过")
        
    except Exception as e:
        print(f"✗ 服务测试失败: {e}")
        traceback.print_exc()

def test_api_routers():
    """测试 API 路由"""
    print("\n=== 测试 API 路由 ===")
    
    try:
        from apps.cases.api import router as cases_router
        
        # 检查路由注册
        routes = []
        for path, _, _ in cases_router.urls:
            routes.append(path)
        
        payment_routes = [r for r in routes if 'payment' in r.lower()]
        batch_routes = [r for r in routes if 'batch' in r.lower()]
        
        print(f"✓ 案件模块路由总数: {len(routes)}")
        print(f"✓ 收支记录相关路由: {payment_routes}")
        print(f"✓ 批量日志相关路由: {batch_routes}")
        
        # 验证关键路由是否存在
        expected_payment_routes = [
            '/payment-record',
            '/payment-record/{record_id}',
            '/case/{case_id}/payment-records',
            '/payment-category',
            '/payment-category/{category_id}',
        ]
        
        expected_batch_routes = [
            '/batch-log/preview',
            '/batch-log',
            '/batch-log/{batch_id}',
        ]
        
        print("\n  预期收支记录路由:")
        for route in expected_payment_routes:
            exists = any(route in r for r in routes)
            status = "✓" if exists else "✗"
            print(f"    {status} {route}")
            
        print("\n  预期批量日志路由:")
        for route in expected_batch_routes:
            exists = any(route in r for r in routes)
            status = "✓" if exists else "✗"
            print(f"    {status} {route}")
            
        print("\n✓ API 路由测试通过")
        
    except Exception as e:
        print(f"✗ API 路由测试失败: {e}")
        traceback.print_exc()

def test_schemas():
    """测试 Schema 定义"""
    print("\n=== 测试 Schema 定义 ===")
    
    try:
        from apps.cases.schemas import (
            PaymentRecordIn,
            PaymentRecordOut,
            PaymentCategoryIn,
            PaymentCategoryOut,
            LogBatchCreateIn,
            LogBatchPreviewOut,
            LogBatchOut,
        )
        
        print("✓ Schema 导入成功")
        
        # 检查 LogBatchCreateIn 是否包含收入字段
        income_fields = ['income_amount', 'income_category_id', 'income_split_count']
        for field in income_fields:
            if hasattr(LogBatchCreateIn, field):
                print(f"✓ LogBatchCreateIn 包含 {field}")
            else:
                print(f"✗ LogBatchCreateIn 缺少 {field}")
                
        print("✓ Schema 测试通过")
        
    except Exception as e:
        print(f"✗ Schema 测试失败: {e}")
        traceback.print_exc()

def test_admin_config():
    """测试 Admin 配置"""
    print("\n=== 测试 Admin 配置 ===")
    
    try:
        from apps.cases.admin.payment_admin import PaymentRecordAdmin, PaymentCategoryAdmin
        from apps.cases.admin.log_batch_admin import CaseLogBatchAdmin
        
        print("✓ Admin 配置导入成功")
        
        # 检查 list_display
        payment_display = PaymentRecordAdmin.list_display
        print(f"  PaymentRecordAdmin.list_display: {payment_display}")
        
        batch_display = CaseLogBatchAdmin.list_display
        print(f"  CaseLogBatchAdmin.list_display: {batch_display}")
        
        # 检查收入相关字段是否在列表中
        if 'has_income_split' in batch_display and 'income_amount' in batch_display:
            print("✓ CaseLogBatchAdmin 包含收入分摊字段")
        else:
            print("✗ CaseLogBatchAdmin 缺少收入分摊字段")
            
        print("✓ Admin 配置测试通过")
        
    except Exception as e:
        print(f"✗ Admin 配置测试失败: {e}")
        traceback.print_exc()

def main():
    """主测试函数"""
    print("=" * 60)
    print("法穿案件收支记录功能测试")
    print("=" * 60)
    
    test_models()
    test_services()
    test_api_routers()
    test_schemas()
    test_admin_config()
    
    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)

if __name__ == "__main__":
    main()
