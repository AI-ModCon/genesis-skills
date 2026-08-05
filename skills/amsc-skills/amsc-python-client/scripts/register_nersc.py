"""Register NERSC facility with an amsc-client Client instance.

Usage in scripts:
    from amsc_client import Client
    client = Client(token="not-needed-for-facilities")

    exec(open(".claude/skills/amsc-python-client/scripts/register_nersc.py").read())
    register_nersc(client)

    nersc = client.facility("nersc")
    compute = nersc.resource("compute")  # Perlmutter
"""


def register_nersc(client):
    """Register NERSC as a facility on the given client."""
    client.register_facility(
        name="nersc",
        base_url="https://api.iri.nersc.gov",
        display_name="National Energy Research Scientific Computing Center",
        auth_method="globus",
        globus_client_id="fae5c579-490a-4d76-b6eb-d78f65caeb63",
        globus_scope=(
            "openid profile email "
            "urn:globus:auth:scope:auth.globus.org:view_identities "
            "https://auth.globus.org/scopes/"
            "ed3e577d-f7f3-4639-b96e-ff5a8445d699/iri_api"
        ),
        globus_resource_server="ed3e577d-f7f3-4639-b96e-ff5a8445d699",
        globus_auth_params={},
    )
