def test_core_schema_module_can_be_imported() -> None:
    import backend.models.schemas as schemas

    assert schemas.__all__ == []
