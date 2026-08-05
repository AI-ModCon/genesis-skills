#!/usr/bin/env python3
"""
Authenticate to the AmSC API with a Globus UserApp and call the API through
an explicit Globus SDK service client.
"""
import argparse
import json
import os
import globus_sdk
from globus_sdk.token_storage import JSONTokenStorage

# Local testing values
# DEFAULT_BASE_URL = "http://0.0.0.0:8000/api/current/"
# AMSC_RESOURCE_SERVER = "08da012c-6998-46f9-9375-a6985ebe3f2b"
# AMSC_SCOPE = "https://auth.globus.org/scopes/08da012c-6998-46f9-9375-a6985ebe3f2b/transfer"


DEFAULT_APP_NAME = "amsc-agent"
CLIENT_ID = "57554043-6dd8-410b-8ece-cd54e9c003bb"
DEFAULT_BASE_URL = "https://api.american-science-cloud.org/api/current"
AMSC_RESOURCE_SERVER = "35bf38d3-4b30-42c8-ac9f-e39cec6516bf"
AMSC_SCOPE = (
    "https://auth.globus.org/scopes/35bf38d3-4b30-42c8-ac9f-e39cec6516bf/amsc"
)
TOKEN_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tokens.json")
app_config = globus_sdk.GlobusAppConfig(
    token_storage=JSONTokenStorage(TOKEN_FILE),
    request_refresh_tokens=True,
    auto_redrive_gares=True,
)


class AmscScopes(globus_sdk.scopes.collection.StaticScopeCollection):
    resource_server = AMSC_RESOURCE_SERVER
    amsc = globus_sdk.scopes.Scope(AMSC_SCOPE)


class AmscServiceClient(globus_sdk.client.BaseClient):
    base_url = DEFAULT_BASE_URL
    scopes = AmscScopes
    service_name = "amsc_service_client"
    default_scope_requirements = [AmscScopes.amsc]

    movement_base_path = "/movement"
    transfer_base_path = f"{movement_base_path}/transfer"
    globus_transfer_base_path = f"{transfer_base_path}/globus"

    def get_api_root(self) -> globus_sdk.response.GlobusHTTPResponse:
        return self.get("/")

    def get_openapi(self) -> globus_sdk.response.GlobusHTTPResponse:
        return self.get("/openapi.json")

    def get_transfers(self) -> globus_sdk.response.GlobusHTTPResponse:
        return self.get(self.transfer_base_path)

    def start_transfer(
        self, payload: dict
    ) -> globus_sdk.response.GlobusHTTPResponse:
        return self.post(self.transfer_base_path, data=payload)

    def start_globus_transfer(
        self, payload: dict
    ) -> globus_sdk.response.GlobusHTTPResponse:
        return self.post(self.globus_transfer_base_path, data=payload)

    def get_globus_transfer(
        self, transfer_id: str
    ) -> globus_sdk.response.GlobusHTTPResponse:
        return self.get(f"{self.globus_transfer_base_path}/{transfer_id}")

    def delete_globus_transfer(
        self, transfer_id: str
    ) -> globus_sdk.response.GlobusHTTPResponse:
        return self.delete(f"{self.globus_transfer_base_path}/{transfer_id}")


def parse_json_payload(raw_payload: str) -> dict:
    payload = json.loads(raw_payload)
    if not isinstance(payload, dict):
        raise ValueError("JSON payload must decode to an object.")
    return payload


def print_response(response: globus_sdk.response.GlobusHTTPResponse) -> None:
    print(json.dumps(response.data, indent=2, sort_keys=True))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Authenticate with Globus and call the AmSC API."
    )
    parser.add_argument(
        "--transfers",
        action="store_true",
        help="Get a list of transfers from the AmSC API.",
    )
    parser.add_argument(
        "--start-transfer",
        metavar="JSON",
        help="Start a transfer from a JSON object payload.",
    )
    parser.add_argument(
        "--start-globus-transfer",
        metavar="JSON",
        help="Start a Globus transfer from a JSON object payload.",
    )
    parser.add_argument(
        "--get-globus-transfer",
        metavar="TRANSFER_ID",
        help="Get a Globus transfer by transfer ID.",
    )
    parser.add_argument(
        "--delete-globus-transfer",
        metavar="TRANSFER_ID",
        help="Delete a Globus transfer by transfer ID.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    with globus_sdk.UserApp(
        DEFAULT_APP_NAME,
        client_id=CLIENT_ID,
        scope_requirements={AMSC_RESOURCE_SERVER: AMSC_SCOPE},
        config=app_config,
    ) as app:
        amsc_client = AmscServiceClient(app=app)
        if args.transfers:
            print_response(amsc_client.get_transfers())
        elif args.start_transfer:
            print_response(
                amsc_client.start_transfer(parse_json_payload(args.start_transfer))
            )
        elif args.start_globus_transfer:
            print_response(
                amsc_client.start_globus_transfer(
                    parse_json_payload(args.start_globus_transfer)
                )
            )
        elif args.get_globus_transfer:
            print_response(amsc_client.get_globus_transfer(args.get_globus_transfer))
        elif args.delete_globus_transfer:
            print_response(
                amsc_client.delete_globus_transfer(args.delete_globus_transfer)
            )
        else:
            print_response(amsc_client.get_api_root())

    return 0


if __name__ == "__main__":
    main()
