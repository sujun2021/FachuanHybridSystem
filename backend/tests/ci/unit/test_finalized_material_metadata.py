from __future__ import annotations

import pytest

from apps.contracts.models import FinalizedMaterial, MaterialCategory
from apps.testing.factories import ContractFactory


@pytest.mark.django_db
def test_finalized_material_save_keeps_relative_file_path_in_sync() -> None:
    contract = ContractFactory()

    material = FinalizedMaterial.objects.create(
        contract=contract,
        file_path="contracts/finalized/10/example.pdf",
        original_filename="example.pdf",
        category=MaterialCategory.ARCHIVE_DOCUMENT,
    )

    assert material.relative_file_path == material.file_path
    assert material.storage_root_type == ""
    assert material.subdir_path == ""

    material.file_path = "contracts/finalized/10/renamed.pdf"
    material.save(update_fields=["file_path"])
    material.refresh_from_db()

    assert material.relative_file_path == material.file_path
