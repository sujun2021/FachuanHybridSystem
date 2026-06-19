"""初始化/删除用户自定义模板。

用法:
    python manage.py init_custom_templates          # 初始化（已存在的跳过）
    python manage.py init_custom_templates --delete # 删除全部自定义模板
    python manage.py init_custom_templates --delete --init  # 先删再建（重建）
"""

from django.core.management.base import BaseCommand

from apps.documents.services.document_template.custom_init_service import CustomTemplateInitService


class Command(BaseCommand):
    help = "初始化或删除用户自定义模板（文件夹+文件模板+绑定关系）"

    def add_arguments(self, parser):
        parser.add_argument(
            "--delete",
            action="store_true",
            help="删除所有自定义模板",
        )
        parser.add_argument(
            "--init",
            action="store_true",
            help="初始化自定义模板（配合 --delete 可重建）",
        )

    def handle(self, **options):
        service = CustomTemplateInitService()

        if options["delete"]:
            result = service.delete_all_custom_templates()
            self.stdout.write(
                self.style.SUCCESS(
                    "删除完成：文件夹 %(folders_deleted)d 个，文件模板 %(documents_deleted)d 个"
                    % result
                )
            )

        if options["init"] or (not options["delete"] and not options["init"]):
            if not options["delete"] and not options["init"]:
                pass  # 默认就是 init
            try:
                result = service.initialize_custom_templates()
            except FileNotFoundError as e:
                self.stderr.write(self.style.ERROR(str(e)))
                return

            if result["success"]:
                self.stdout.write(
                    self.style.SUCCESS(
                        "初始化完成！文件夹 %(folder_created)d 个，"
                        "文件模板 %(doc_created)d 个，绑定 %(binding_created)d 个"
                        % result
                    )
                )
            else:
                self.stderr.write(
                    self.style.ERROR(
                        "初始化失败：缺少 %(count)d 个文件"
                        % {"count": len(result["missing_files"])}
                    )
                )
                for f in result["missing_files"][:10]:
                    self.stderr.write(f"  - {f}")
