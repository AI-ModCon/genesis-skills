"""Build the minimal environment exposed to Promptfoo subprocesses."""

import os


# Promptfoo needs its executable search path and, depending on the runtime,
# its user/configuration directories. The remaining entries are explicit
# skill inputs used for authentication, remote generation, or provider config.
PROMPTFOO_ENVIRONMENT_KEYS = frozenset(
    {
        "PATH",
        "HOME",
        "USERPROFILE",
        "XDG_CONFIG_HOME",
        "XDG_DATA_HOME",
        "PROMPTFOO_HOST",
        "PROMPTFOO_API_KEY",
        "PROMPTFOO_DISABLE_REDTEAM_REMOTE_GENERATION",
        "MODEL",
        "MODEL_ENDPOINT",
        "MODEL_AUTH_TOKEN",
    }
)


def promptfoo_environment(phase: str | None = None) -> dict[str, str]:
    """Return only variables required by Promptfoo and its configured provider."""
    environment = {
        key: value
        for key, value in os.environ.items()
        if key in PROMPTFOO_ENVIRONMENT_KEYS
    }
    if phase == "evaluate":
        # Failed assertions are findings, not an operational runner failure.
        environment["PROMPTFOO_FAILED_TEST_EXIT_CODE"] = "0"
    return environment
