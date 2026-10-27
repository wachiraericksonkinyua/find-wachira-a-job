from app import match


def test_parse_match_json_strips_fences_and_clamps():
    high = match._parse_match_json(
        '```json\n'
        '{"score": 150, "verdict": "Strong match.", '
        '"matched_skills": ["Python"], "gaps": []}\n'
        '```'
    )
    assert high is not None
    assert high["score"] == 100

    low = match._parse_match_json(
        '{"score": -20, "verdict": "Weak match.", '
        '"matched_skills": [], "gaps": ["Docker"]}'
    )
    assert low is not None
    assert low["score"] == 0
    assert low["gaps"] == ["Docker"]


def test_parse_match_json_rejects_malformed():
    assert match._parse_match_json("not json") is None
    assert match._parse_match_json('{"score": 50, "verdict": ""}') is None


def test_run_match_uses_deterministic_fallback_and_vector_citations(monkeypatch):
    monkeypatch.setattr(
        match,
        "sync_embeddings",
        lambda: {
            "embedded": 0,
            "cached": 6,
            "pruned": 0,
            "total": 6,
            "postgres": False,
        },
    )
    monkeypatch.setattr(
        match,
        "search_similar_chunks",
        lambda query, top_k=4: [
            {
                "project_slug": "ayutech",
                "project_title": "AyuTech",
                "section": "build",
                "text": "FastAPI + M-Pesa",
                "score": 0.8,
            }
        ],
    )

    def fail_llm(*args, **kwargs):
        raise match.LLMError("offline")

    monkeypatch.setattr(match, "complete", fail_llm)

    result = match.run_match(
        match.MatchRequest(
            role="Backend Engineer",
            jd="Python FastAPI PostgreSQL M-Pesa backend role.",
        )
    )

    assert 0 <= result.score <= 100
    assert result.citations[0].project_slug == "ayutech"
    assert result.citations[0].similarity == 0.8
    assert "Python" in result.matched_skills
    assert "Deterministic" in result.verdict


def test_run_match_uses_keyword_citations_when_retrieval_fails(monkeypatch):
    def fail_retrieval(*args, **kwargs):
        raise RuntimeError("offline")

    def fail_llm(*args, **kwargs):
        raise match.LLMError("offline")

    monkeypatch.setattr(match, "sync_embeddings", fail_retrieval)
    monkeypatch.setattr(match, "search_similar_chunks", fail_retrieval)
    monkeypatch.setattr(match, "complete", fail_llm)

    result = match.run_match(
        match.MatchRequest(jd="Python FastAPI PostgreSQL Vue.js M-Pesa backend role.")
    )

    assert result.citations
    assert all(citation.project_slug for citation in result.citations)
    assert result.citations[0].similarity >= 0
