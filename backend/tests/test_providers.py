from app.agents.contracts import SearchBriefInput
from app.providers.commute.mock import MockCommuteProvider
from app.providers.geocode.mock import MockGeocoder
from app.providers.llm.embeddings import MockEmbeddings, cosine_similarity
from app.providers.llm.mock import MockLLMProvider
from app.services.llm import LLMService, resolve_model


async def test_mock_geocoder_landmarks_and_jitter() -> None:
    geo = MockGeocoder()
    caltrain = await geo.geocode("Sunnyvale Caltrain")
    assert caltrain == (37.3783, -122.0306)
    a = await geo.geocode("123 Fake St, Santa Clara")
    b = await geo.geocode("123 Fake St, Santa Clara")
    assert a == b  # deterministic
    assert a is not None and abs(a[0] - 37.3541) < 0.02
    assert await geo.geocode("1 Nowhere Plaza, Anchorage, AK") is None


async def test_mock_commute_peak_slower_and_deterministic() -> None:
    provider = MockCommuteProvider()
    origin, dest = (37.3688, -122.0363), (37.3541, -121.9552)
    peak = await provider.estimate(origin, dest, "drive", "peak")
    offpeak = await provider.estimate(origin, dest, "drive", "offpeak")
    assert peak.minutes > offpeak.minutes
    again = await provider.estimate(origin, dest, "drive", "peak")
    assert peak.minutes == again.minutes
    walk = await provider.estimate(origin, dest, "walk", "peak")
    assert walk.minutes > peak.minutes  # walking across towns takes longer


async def test_mock_isochrone_is_closed_polygon() -> None:
    provider = MockCommuteProvider()
    feature = await provider.isochrone((37.3688, -122.0363), "drive", 25)
    geometry = feature["geometry"]
    assert isinstance(geometry, dict)
    ring = geometry["coordinates"][0]
    assert ring[0] == ring[-1]
    assert len(ring) == 37


async def test_mock_embeddings_similarity_orders_sensibly() -> None:
    emb = MockEmbeddings()
    vectors = await emb.embed(
        ["roaches in the kitchen", "cockroaches in the kitchen sink", "parking garage is tight"]
    )
    same_topic = cosine_similarity(vectors[0], vectors[1])
    different = cosine_similarity(vectors[0], vectors[2])
    assert same_topic > different


async def test_llm_service_mock_brief_parse_and_accounting(client: object) -> None:
    service = LLMService(provider=MockLLMProvider())
    result = await service.call(
        agent="orchestrator",
        task="brief_parse",
        schema=SearchBriefInput,
        context={
            "text": "2b2b under $3,800 near Sunnyvale Caltrain, 20 min to Santa Clara, dog friendly"
        },
        text="2b2b under $3,800 near Sunnyvale Caltrain, 20 min to Santa Clara, dog friendly",
    )
    brief = result.data
    assert brief.budget_max == 3800
    assert brief.beds == 2 and brief.baths == 2
    assert "dog" in brief.pets
    assert any("Santa Clara" in p.label for p in brief.important_places)
    assert result.cost_usd > 0
    assert result.tokens_in > 0


def test_model_routing_tiers() -> None:
    fast = resolve_model("anthropic", "brief_parse")
    strong = resolve_model("anthropic", "clause_risk")
    assert fast.model == "claude-haiku-5-5"
    assert strong.model == "claude-opus-5-5"
    mock_fast = resolve_model("mock", "brief_parse")
    assert mock_fast.model == "mock-fast"
