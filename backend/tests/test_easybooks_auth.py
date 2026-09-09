"""Credential login and token renewal. All values here are synthetic."""

import httpx
import pytest
from app.config import Settings
from app.integrations.easybooks.client import (
    AUTHENTICATE_PATH,
    PRE_LOGIN_PATH,
    SALES_LIST_PATH,
    EasyBooksAuthError,
    EasyBooksConfigurationError,
    HttpxReadOnlyTransport,
    _org_from_trees,
    _token_from,
)

SYNTHETIC_ORG = "00000000-0000-4000-8000-000000000001"
ONE_ORG = {"isOTP": False, "orgTrees": [{"parent": {"id": SYNTHETIC_ORG}}]}


def _ok_login(token="fresh-token"):
    return [
        (PRE_LOGIN_PATH, httpx.Response(200, json=ONE_ORG)),
        (AUTHENTICATE_PATH, httpx.Response(200, json={"id_token": token})),
    ]


def _response(payload=None, headers=None):
    return httpx.Response(200, json=payload if payload is not None else {}, headers=headers or {})

# HTTP 500 carrying Spring Security's access-denied path, as EasyBooks answers a
# rejected credential.
AUTH_DENIED = {
    "code": 500,
    "status": "INTERNAL_SERVER_ERROR",
    "message": "org.springframework.security.web.access.ExceptionTranslationFilter",
}


def _settings(**overrides):
    return Settings(
        **{
            "easybooks_live_enabled": True,
            "easybooks_group": "FIXTURE-GROUP",
            "easybooks_username": "uniops-service",
            "easybooks_password": "synthetic-password",
            **overrides,
        }
    )


def _scripted(transport, script):
    """Drive a transport from a list of (path_predicate, response) handlers."""
    calls = []

    def handle(request):
        calls.append((request.url.path, request.content))
        for path, response in script:
            if request.url.path == path:
                return response() if callable(response) else response
        raise AssertionError(f"unscripted path {request.url.path}")

    transport._client = httpx.Client(
        transport=httpx.MockTransport(handle),
        base_url="https://easybooks.invalid",
        headers=dict(transport._client.headers),
    )
    return calls


def test_credentials_alone_are_enough_to_start_live_mode(monkeypatch):
    logins = []

    def fake_login(self):
        logins.append(True)
        self._client.headers["Authorization"] = "Bearer synthetic"

    monkeypatch.setattr(HttpxReadOnlyTransport, "_log_in", fake_login)
    transport = HttpxReadOnlyTransport(_settings())

    assert logins == [True]
    assert transport._client.headers["Authorization"] == "Bearer synthetic"


def test_a_configured_token_is_used_without_logging_in(monkeypatch):
    monkeypatch.setattr(
        HttpxReadOnlyTransport,
        "_log_in",
        lambda self: pytest.fail("must not log in when a token is configured"),
    )
    transport = HttpxReadOnlyTransport(_settings(easybooks_bearer_token="operator-supplied"))

    assert transport._client.headers["Authorization"] == "Bearer operator-supplied"


def test_login_sends_the_observed_two_step_payloads(monkeypatch):
    """Signing in without an org yields a token the data API refuses."""
    import json

    monkeypatch.setattr(HttpxReadOnlyTransport, "_log_in", lambda self: None)
    transport = HttpxReadOnlyTransport(_settings())
    monkeypatch.undo()
    calls = _scripted(transport, _ok_login())

    transport._log_in()

    assert [path for path, _ in calls] == [PRE_LOGIN_PATH, AUTHENTICATE_PATH]
    assert json.loads(calls[0][1]) == {
        "username": "uniops-service",
        "password": "synthetic-password",
        "rememberMe": False,
    }
    assert json.loads(calls[1][1]) == {
        "username": "uniops-service",
        "password": "synthetic-password",
        "rememberMe": False,
        "org": SYNTHETIC_ORG,
        "otp": False,
        "secretCode": "",
    }
    assert transport._client.headers["Authorization"] == "Bearer fresh-token"


def test_a_configured_org_overrides_discovery(monkeypatch):
    import json

    monkeypatch.setattr(HttpxReadOnlyTransport, "_log_in", lambda self: None)
    transport = HttpxReadOnlyTransport(_settings(easybooks_org="configured-org"))
    monkeypatch.undo()
    calls = _scripted(transport, _ok_login())

    transport._log_in()

    assert json.loads(calls[1][1])["org"] == "configured-org"


def test_an_account_needing_an_otp_is_refused_with_an_explanation(monkeypatch):
    monkeypatch.setattr(HttpxReadOnlyTransport, "_log_in", lambda self: None)
    transport = HttpxReadOnlyTransport(_settings())
    monkeypatch.undo()
    calls = _scripted(
        transport, [(PRE_LOGIN_PATH, httpx.Response(200, json={"isOTP": True, "orgTrees": []}))]
    )

    with pytest.raises(EasyBooksAuthError, match="one-time password"):
        transport._log_in()

    # It stops at pre-login; no point attempting authenticate.
    assert [path for path, _ in calls] == [PRE_LOGIN_PATH]


def test_a_rejected_token_is_renewed_once_and_the_request_retried(monkeypatch):
    monkeypatch.setattr(HttpxReadOnlyTransport, "_log_in", lambda self: None)
    transport = HttpxReadOnlyTransport(_settings(easybooks_bearer_token="stale-token"))
    monkeypatch.undo()

    answers = iter([httpx.Response(500, json=AUTH_DENIED), httpx.Response(200, json=[{"id": "1"}])])
    calls = _scripted(
        transport, [(SALES_LIST_PATH, lambda: next(answers)), *_ok_login("renewed-token")]
    )

    assert transport.request("GET", SALES_LIST_PATH) == [{"id": "1"}]
    assert [path for path, _ in calls] == [
        SALES_LIST_PATH,
        PRE_LOGIN_PATH,
        AUTHENTICATE_PATH,
        SALES_LIST_PATH,
    ]
    assert transport._client.headers["Authorization"] == "Bearer renewed-token"


def test_a_renewed_token_that_is_also_rejected_does_not_loop(monkeypatch):
    monkeypatch.setattr(HttpxReadOnlyTransport, "_log_in", lambda self: None)
    transport = HttpxReadOnlyTransport(_settings(easybooks_bearer_token="stale-token"))
    monkeypatch.undo()

    calls = _scripted(
        transport, [(SALES_LIST_PATH, httpx.Response(500, json=AUTH_DENIED)), *_ok_login()]
    )

    with pytest.raises(EasyBooksAuthError):
        transport.request("GET", SALES_LIST_PATH)

    # Exactly one renewal attempt, not an endless refresh loop.
    assert [path for path, _ in calls].count(AUTHENTICATE_PATH) == 1


def test_without_credentials_a_rejected_token_is_not_renewed(monkeypatch):
    transport = HttpxReadOnlyTransport(
        _settings(
            easybooks_bearer_token="stale-token", easybooks_username=None, easybooks_password=None
        )
    )
    calls = _scripted(transport, [(SALES_LIST_PATH, httpx.Response(500, json=AUTH_DENIED))])

    with pytest.raises(EasyBooksAuthError, match="most likely expired"):
        transport.request("GET", SALES_LIST_PATH)

    assert [path for path, _ in calls] == [SALES_LIST_PATH]


def test_bad_credentials_are_reported_without_echoing_them(monkeypatch):
    monkeypatch.setattr(HttpxReadOnlyTransport, "_log_in", lambda self: None)
    transport = HttpxReadOnlyTransport(_settings())
    monkeypatch.undo()
    denied = httpx.Response(500, json={"message": "User not found"})
    _scripted(transport, [(PRE_LOGIN_PATH, denied)])

    with pytest.raises(EasyBooksAuthError) as caught:
        transport._log_in()

    message = str(caught.value)
    assert "UNIOPS_EASYBOOKS_PASSWORD" in message
    assert "synthetic-password" not in message
    assert "uniops-service" not in message


@pytest.mark.parametrize(
    "key", ["id_token", "idToken", "token", "access_token", "accessToken", "jwt"]
)
def test_the_usual_token_spellings_are_all_accepted(key):
    assert _token_from(_response({key: "t"})) == "t"


def test_a_token_returned_only_in_the_authorization_header_is_accepted():
    """The web client honours either, so both are read."""
    assert _token_from(_response({}, {"Authorization": "Bearer header-token"})) == "header-token"


@pytest.mark.parametrize("payload", [{}, {"unexpected": "shape"}, {"id_token": "  "}, [], "text"])
def test_an_unrecognisable_authenticate_response_is_refused_not_guessed(payload):
    with pytest.raises(EasyBooksAuthError, match="no recognisable token"):
        _token_from(_response(payload))


def test_the_refusal_names_what_came_back_so_it_can_be_diagnosed():
    with pytest.raises(EasyBooksAuthError, match="expiresIn"):
        _token_from(_response({"expiresIn": 3600, "unexpected": "shape"}))


def test_a_single_organisation_is_chosen_automatically():
    assert _org_from_trees(ONE_ORG) == SYNTHETIC_ORG


def test_an_ambiguous_organisation_must_be_configured_not_guessed():
    two = {"orgTrees": [{"parent": {"id": "org-a"}}, {"parent": {"id": "org-b"}}]}
    with pytest.raises(EasyBooksAuthError, match="UNIOPS_EASYBOOKS_ORG"):
        _org_from_trees(two)


def test_no_organisation_offered_is_also_refused():
    with pytest.raises(EasyBooksAuthError, match="UNIOPS_EASYBOOKS_ORG"):
        _org_from_trees({"orgTrees": []})


def test_live_mode_still_needs_some_credential():
    with pytest.raises(EasyBooksConfigurationError, match="bearer token, session cookie"):
        HttpxReadOnlyTransport(
            _settings(easybooks_username=None, easybooks_password=None)
        )


def test_a_username_without_a_password_is_not_a_credential():
    with pytest.raises(EasyBooksConfigurationError, match="bearer token, session cookie"):
        HttpxReadOnlyTransport(_settings(easybooks_password=None))


def test_authenticate_is_the_only_extra_post_allowed(monkeypatch):
    monkeypatch.setattr(HttpxReadOnlyTransport, "_log_in", lambda self: None)
    transport = HttpxReadOnlyTransport(_settings())

    with pytest.raises(EasyBooksConfigurationError, match="POST is not allowed"):
        transport.request("POST", "/api/some-other-write")
