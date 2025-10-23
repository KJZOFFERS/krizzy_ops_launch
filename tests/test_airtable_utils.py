from __future__ import annotations

import airtable_utils as au


class DummyTable:
    def __init__(self):
        self.created = []
        self.updated = []
        self.records = []

    def all(
        self, filterByFormula: str | None = None, page_size: int = 100
    ):  # noqa: N803 - external API
        if not filterByFormula:
            return list(self.records)
        key = filterByFormula.split("'")[-2]
        for r in self.records:
            if r["fields"].get("source_id") == key:
                return [r]
        return []

    def create(self, record, typecast=True):  # noqa: ANN001 - external API
        rid = f"rec{len(self.records)+1}"
        wrapped = {"id": rid, "fields": record}
        self.records.append(wrapped)
        self.created.append(record)
        return wrapped

    def update(self, rec_id, record, typecast=True):  # noqa: ANN001 - external API
        for idx, r in enumerate(self.records):
            if r["id"] == rec_id:
                self.records[idx] = {"id": rec_id, "fields": record}
                self.updated.append(record)
                return self.records[idx]
        raise AssertionError("Record not found")


def test_safe_airtable_write_upsert(monkeypatch):
    dummy_table = DummyTable()

    def fake_get_table(name: str):  # noqa: ARG001
        return dummy_table

    monkeypatch.setattr(au, "_get_table", fake_get_table)

    rec1 = {"source_id": "abc", "x": 1}
    out1 = au.safe_airtable_write("T", rec1, key_fields=["source_id"])
    assert out1["fields"]["x"] == 1
    assert len(dummy_table.created) == 1

    rec2 = {"source_id": "abc", "x": 2}
    out2 = au.safe_airtable_write("T", rec2, key_fields=["source_id"])
    assert out2["fields"]["x"] == 2
    assert len(dummy_table.updated) == 1
