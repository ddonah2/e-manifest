import os

import pytest
import requests
import responses

from . import RCRAINFO_PREPROD, RcrainfoClient, RcrainfoResponse, new_client

MOCK_MTN = "100032437ELC"
MOCK_GEN_ID = "VATESTGEN001"
MOCK_API_ID = "mock_api_id"
MOCK_API_KEY = "mock_api_key"


@pytest.fixture
def mock_response():
    token_expiration = "2053-08-04T22:24:42.724+00:00"
    with responses.RequestsMock() as resp:
        resp.add(
            responses.GET,
            f"{RCRAINFO_PREPROD}v1/auth/{MOCK_API_ID}/{MOCK_API_KEY}",
            json={
                "token": "mock_token",
                "expiration": token_expiration,
            },
        )
        yield resp


class TestRcrainfoClient:
    api_id = MOCK_API_ID
    api_key = MOCK_API_KEY
    rcrainfo = RcrainfoClient("preprod", api_id=api_id, api_key=api_key)

    def test_zip_attribute_is_none_when_attachment_not_returned(self, mock_response):
        # Arrange
        mock_response.add(
            # Add mock response for site-details endpoint
            responses.GET,
            f"{self.rcrainfo.base_url}v1/site-details/{MOCK_GEN_ID}",
            json={
                "epaSiteId": MOCK_GEN_ID,
            },
        )
        # Act
        rcra_response = self.rcrainfo.get_site(MOCK_GEN_ID)
        # Assert
        assert rcra_response.zip is None

    def test_token_when_is_authenticated(self, mock_response):
        # Arrange
        client = RcrainfoClient("preprod")
        # Act
        client.authenticate(api_id=MOCK_API_ID, api_key=MOCK_API_KEY)
        # Assert
        assert isinstance(client.token, str) and client.is_authenticated

    def test_token_is_none_when_not_authenticated(self):
        new_rcrainfo = RcrainfoClient("preprod")
        assert new_rcrainfo.token is None and not new_rcrainfo.is_authenticated

    def test_extracted_response_json_matches(self, mock_response):
        # Arrange
        rcrainfo = new_client(
            "preprod", api_id=self.api_id, api_key=self.api_key, auto_renew=True
        )
        mock_response.add(
            # Add mock response for site-details endpoint
            responses.GET,
            f"{self.rcrainfo.base_url}v1/site-details/{MOCK_GEN_ID}",
            json={
                "epaSiteId": MOCK_GEN_ID,
            },
        )
        # Act
        resp: RcrainfoResponse = rcrainfo.get_site(MOCK_GEN_ID)
        # Assert
        assert resp.response.json() == resp.json()


class TestRcrainfoClientIsExtendable:
    class MyClass(RcrainfoClient):
        mock_api_id_from_external = "an_api_id_from_someplace_else"
        mock_api_key_from_external = "a_api_key_from_someplace_else"

        def retrieve_id(self, api_id=None) -> str:
            """
            This example method on our test subclass shows we can override the set_api_id method
            if the user wants to get their api ID from somewhere else (e.g., a service, or database)
            """
            returned_string = (
                self.mock_api_id_from_external
            )  # You could get this primitive value from anywhere
            return super().retrieve_id(returned_string)

        def retrieve_key(self, api_key=None) -> str:
            """
            This example method on our test subclass shows we can override the set_api_key method
            """
            returned_string = (
                self.mock_api_key_from_external
            )  # You could get this primitive value from anywhere
            return super().retrieve_id(returned_string)

    def test_retrieve_id_override(self):
        my_subclass = self.MyClass("preprod")
        api_id_set_during_auth = my_subclass.retrieve_id()
        assert api_id_set_during_auth == self.MyClass.mock_api_id_from_external

    def test_retrieve_key_override(self):
        my_subclass = self.MyClass("preprod")
        api_key_set_during_auth = my_subclass.retrieve_key()
        assert api_key_set_during_auth == self.MyClass.mock_api_key_from_external

    def test_retrieve_key_returns_string(self):
        my_subclass = self.MyClass("preprod")
        api_key_set_during_auth = my_subclass.retrieve_key()
        assert api_key_set_during_auth == self.MyClass.mock_api_key_from_external


class TestAutoAuthentication:
    api_id = MOCK_API_ID
    api_key = MOCK_API_KEY

    @responses.activate
    def test_not_automatically_authenticates_by_default(self):
        """
        RcrainfoClient does not automatically authenticate (via the auth endpoint) by default
        """
        # Arrange
        rcrainfo = new_client("preprod", api_id=self.api_id, api_key=self.api_key)
        responses.add(
            # Add mock response for site-details endpoint
            responses.GET,
            f"{rcrainfo.base_url}v1/emanifest/manifest/{MOCK_MTN}",
            json={
                "manifestTrackingNumber": MOCK_MTN,
            },
        )
        auth_response = responses.add(
            responses.GET,
            f"{RCRAINFO_PREPROD}v1/auth/{MOCK_API_ID}/{MOCK_API_KEY}",
            json={
                "token": "mock_token",
                "expiration": "mock_expiration",
            },
        )
        # Act
        _resp = rcrainfo.get_manifest(MOCK_MTN)
        # Assert
        assert auth_response.call_count == 0

    @responses.activate
    def test_authenticates_when_auto_renew_set_to_true(self):
        # Arrange
        # create a new auto authenticating client
        rcrainfo = new_client(
            "preprod", api_id=self.api_id, api_key=self.api_key, auto_renew=True
        )
        responses.add(
            # Add mock response for site-details endpoint
            responses.GET,
            f"{rcrainfo.base_url}v1/emanifest/manifest/{MOCK_MTN}",
            json={
                "manifestTrackingNumber": MOCK_MTN,
            },
        )
        auth_response = responses.add(
            responses.GET,
            f"{RCRAINFO_PREPROD}v1/auth/{MOCK_API_ID}/{MOCK_API_KEY}",
            json={
                "token": "mock_token",
                "expiration": "mock_expiration",
            },
        )
        _resp = rcrainfo.get_manifest(MOCK_MTN)
        assert auth_response.call_count > 0

    def test_non_present_credentials_does_not_auth(self):
        new_rcrainfo = RcrainfoClient("preprod")
        _mtn = new_rcrainfo.get_manifest(MOCK_MTN)
        assert not new_rcrainfo.is_authenticated


class TestSessionSuperClassIsUsable:
    api_id = os.getenv("RCRAINFO_API_ID")
    api_key = os.getenv("RCRAINFO_API_KEY")
    rcrainfo = RcrainfoClient("preprod", api_key=api_key, api_id=api_id)

    def test_can_use_hooks(self):
        test_string = "foobar"

        def mock_hook(resp: requests.Response, *args, **kwargs):
            """
            Hooks can be used on various phases of the http lifecycle.
            This functionality comes from request.Session class
            https://requests.readthedocs.io/en/latest/user/advanced/#session-objects
            """
            resp.reason = test_string
            return resp

        self.rcrainfo.hooks = {"response": mock_hook}
        hooked_resp = self.rcrainfo.get_manifest(MOCK_MTN)
        assert hooked_resp.response.reason is test_string


class TestBadClient:
    bad_rcrainfo = RcrainfoClient("preprod")

    # test of initial state
    def test_bad_auth(self):
        self.bad_rcrainfo.authenticate(os.getenv("RCRAINFO_API_ID"), "a_bad_api_key")
        assert self.bad_rcrainfo.token is None

    def test_client_token_state(self):
        assert self.bad_rcrainfo.token is None


class TestNewClientConstructor:
    def test_returns_instance_of_client(self):
        rcrainfo = new_client("prod")
        preprod = new_client("preprod")
        blank = new_client()
        assert isinstance(rcrainfo, RcrainfoClient)
        assert isinstance(preprod, RcrainfoClient)
        assert isinstance(blank, RcrainfoClient)

    def test_new_client_defaults_to_preprod(self):
        rcrainfo = new_client()
        assert rcrainfo.base_url == RCRAINFO_PREPROD
