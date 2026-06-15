# Generated migration — make payment record fields optional
from __future__ import annotations

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("cases", "0026_add_performance_indexes_round2"),
    ]

    operations = [
        migrations.AlterField(
            model_name="casepaymentrecord",
            name="direction",
            field=models.CharField(
                blank=True,
                choices=[("income", "收入"), ("expense", "支出")],
                default="",
                max_length=16,
                verbose_name="收支方向",
            ),
        ),
        migrations.AlterField(
            model_name="casepaymentrecord",
            name="amount",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=14,
                null=True,
                verbose_name="金额",
            ),
        ),
        migrations.AlterField(
            model_name="casepaymentrecord",
            name="purpose",
            field=models.CharField(
                blank=True,
                choices=[
                    ("counterparty_payment", "相对方主动支付"),
                    ("enforcement_recovery", "执行回款"),
                    ("court_fee_refund", "法院退还诉讼费"),
                    ("settlement", "和解款"),
                    ("court_fee", "诉讼费"),
                    ("preservation_fee", "诉讼保全费"),
                    ("property_preservation_fee", "财产保全费"),
                    ("announcement_fee", "公告费"),
                    ("execution_fee", "执行费"),
                    ("appraisal_fee", "鉴定费"),
                    ("attorney_fee", "律师费"),
                    ("travel_fee", "差旅费"),
                    ("investigation_fee", "调查费"),
                    ("property_insurance_fee", "财产保险费"),
                    ("guarantee_fee", "保函费"),
                    ("notary_fee", "公证费"),
                    ("assessment_fee", "评估费"),
                    ("express_fee", "快递费"),
                    ("other_expense", "其他费用"),
                ],
                default="",
                max_length=64,
                verbose_name="款项用途",
            ),
        ),
    ]
