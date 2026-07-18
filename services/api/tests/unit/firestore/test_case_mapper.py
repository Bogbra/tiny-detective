from app.infrastructure.firestore.case_mapper import case_to_document, document_to_case


def test_round_trip_preserves_all_fields(make_case):
    case = make_case()

    document = case_to_document(case)
    restored = document_to_case(case.case_id.value, document)

    assert restored == case


def test_document_uses_camel_case_field_names(make_case):
    case = make_case()

    document = case_to_document(case)

    assert set(document.keys()) == {
        "title",
        "setting",
        "problem",
        "suspects",
        "clues",
        "solution",
        "difficulty",
        "locale",
        "status",
        "createdAt",
        "updatedAt",
        "source",
    }
    assert set(document["suspects"][0].keys()) == {
        "suspectId",
        "name",
        "role",
        "publicStatement",
        "isCulprit",
        "privateReasoning",
        "personality",
    }
    assert set(document["clues"][0].keys()) == {
        "clueId",
        "text",
        "relevance",
        "relatedSuspectIds",
        "unlockOrder",
    }
    assert set(document["solution"].keys()) == {
        "culpritSuspectId",
        "explanation",
        "requiredClueIds",
    }


def test_source_defaults_to_curated(make_case):
    case = make_case()

    assert case.source == "curated"
    document = case_to_document(case)
    assert document["source"] == "curated"


def test_live_generated_source_round_trips(make_case):
    case = make_case(source="live_generated")

    document = case_to_document(case)
    restored = document_to_case(case.case_id.value, document)

    assert document["source"] == "live_generated"
    assert restored.source == "live_generated"


def test_missing_source_field_defaults_to_curated(make_case):
    """Backward compatibility: the two cases already in production Firestore
    were written before this field existed — document_to_case must not
    crash on documents that predate it."""
    case = make_case()
    document = case_to_document(case)
    del document["source"]

    restored = document_to_case(case.case_id.value, document)

    assert restored.source == "curated"


def test_document_includes_private_fields(make_case):
    """The stored document MUST include solution/private data — the backend
    needs it server-side. Separation from players happens at the API layer
    (case.public_view()), not by omitting it from storage. See
    test_public_private_separation.py for the end-to-end proof."""
    case = make_case()

    document = case_to_document(case)

    assert "culpritSuspectId" in document["solution"]
    assert any(s["isCulprit"] for s in document["suspects"])
    assert any(s["privateReasoning"] for s in document["suspects"])
