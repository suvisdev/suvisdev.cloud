from __future__ import annotations

import pytest
from fakes import (
    BOT,
    HUMAN,
    _FakeEventRepository,
    _FakeModel,
    _FakeSiteRepository,
    _FakeVelocity,
    make_site,
)

from deolmi.adapter.outbound.security.jwt_score_token_adapter import JwtScoreTokenAdapter
from deolmi.app.dtos.score_dto import ScoreCommand, VerifyCommand
from deolmi.app.dtos.site_dto import SiteCreateCommand
from deolmi.app.errors import (
    BadSecretError,
    OriginNotAllowedError,
    TokenReusedError,
    UnknownSiteError,
)
from deolmi.app.use_cases.score_interactor import ScoreInteractor
from deolmi.app.use_cases.site_admin_interactor import SiteAdminInteractor
from deolmi.domain.services.site_keys import secret_matches


def _interactor(*, model=None, events=None, velocity=None, site=None):
    return ScoreInteractor(
        sites=_FakeSiteRepository(site or make_site()),
        events=events or _FakeEventRepository(),
        model=model or _FakeModel(),
        tokens=JwtScoreTokenAdapter("test-secret"),
        velocity=velocity or _FakeVelocity(),
    )


def _cmd(signals, site_key="pk_test", origin=None):
    return ScoreCommand(site_key=site_key, signals=signals, origin=origin, client_ip="1.2.3.4")


@pytest.mark.asyncio
async def test_human_goes_through_model_and_is_allowed():
    model, events = _FakeModel(0.2), _FakeEventRepository()
    it = _interactor(model=model, events=events)
    issued = await it.score(_cmd(HUMAN))
    assert issued.verdict == "allow" and model.calls == 1
    result = events.rows[0][3]
    assert result.decided_by == "model" and result.model_score == 0.2


@pytest.mark.asyncio
async def test_rule_block_skips_model_cheap_first():
    model = _FakeModel(0.1)
    it = _interactor(model=model)
    issued = await it.score(_cmd(BOT))
    assert issued.verdict == "block" and model.calls == 0


@pytest.mark.asyncio
async def test_model_can_raise_score_above_rules():
    it = _interactor(model=_FakeModel(0.7))
    assert (await it.score(_cmd(HUMAN))).verdict == "challenge"


@pytest.mark.asyncio
async def test_velocity_is_counted_per_site_and_ip_and_can_block():
    velocity = _FakeVelocity(count=60)
    it = _interactor(velocity=velocity)
    assert (await it.score(_cmd(HUMAN))).verdict == "block"
    assert velocity.keys == ["pk_test:1.2.3.4"]


@pytest.mark.asyncio
async def test_unknown_site_rejected():
    with pytest.raises(UnknownSiteError):
        await _interactor().score(_cmd(HUMAN, site_key="pk_nope"))


@pytest.mark.asyncio
async def test_foreign_origin_rejected():
    it = _interactor(site=make_site(domains=("ticket.example.com",)))
    with pytest.raises(OriginNotAllowedError):
        await it.score(_cmd(HUMAN, origin="https://evil.com"))
    assert (await it.score(_cmd(HUMAN, origin="https://ticket.example.com"))).verdict == "allow"


@pytest.mark.asyncio
async def test_event_save_failure_does_not_block_scoring():
    it = _interactor(events=_FakeEventRepository(fail=True))
    assert (await it.score(_cmd(HUMAN))).token


@pytest.mark.asyncio
async def test_verify_returns_full_result_once():
    it = _interactor()
    token = (await it.score(_cmd(BOT))).token
    result = await it.verify(VerifyCommand(secret="sk_test", token=token))
    assert result.verdict == "block" and result.model_score is None and result.reasons
    with pytest.raises(TokenReusedError):
        await it.verify(VerifyCommand(secret="sk_test", token=token))


@pytest.mark.asyncio
async def test_wrong_secret_does_not_burn_the_token():
    it = _interactor()
    token = (await it.score(_cmd(HUMAN))).token
    with pytest.raises(BadSecretError):
        await it.verify(VerifyCommand(secret="sk_wrong", token=token))
    assert (await it.verify(VerifyCommand(secret="sk_test", token=token))).verdict == "allow"


@pytest.mark.asyncio
async def test_create_site_returns_secret_once_and_stores_only_hash():
    sites = _FakeSiteRepository()
    admin = SiteAdminInteractor(sites=sites, events=_FakeEventRepository(), model=_FakeModel())
    issued = await admin.create_site(
        SiteCreateCommand(name="예매처", plan="pro", domains=("a.com",))
    )
    stored = sites.sites[issued.site.site_key]
    assert issued.secret_key not in stored.secret_hash
    assert secret_matches(issued.secret_key, stored.secret_hash)
    assert "secret" not in issued.site.to_schema().model_dump()
    assert issued.to_schema().secret_key == issued.secret_key
