"""
Michito B2B Engine — Central Configuration & Environment Loader.
Supports clean multi-environment loading:
  1. .env.local (Local developer machine overrides)
  2. .env.stg (Staging environment)
  3. .env (Production / default base environment)
  4. Google Secret Manager / Cloud Run native environment injection (takes highest priority)
"""

import os
from pathlib import Path


def load_env_file(filepath: Path) -> None:
    """Parses a standard .env file and sets variables in os.environ if not already defined."""
    if not filepath.exists():
        return
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip().strip("'\"")
                # Environment variables already set (e.g. injected by Cloud Run or Docker) are preserved
                if key not in os.environ:
                    os.environ[key] = val
    except Exception:
        pass


def init_environment() -> str:
    root_dir = Path(__file__).resolve().parent.parent
    env_name = os.environ.get("ENVIRONMENT", "development").lower()

    # Precedence:
    # 1. .env.local (Local developer machine overrides)
    # 2. .env.stg (Staging)
    # 3. .env (Production / base)
    local_env = root_dir / ".env.local"
    stg_env = root_dir / ".env.stg"
    prod_env = root_dir / ".env"

    if local_env.exists():
        load_env_file(local_env)
    elif env_name == "staging" and stg_env.exists():
        load_env_file(stg_env)
    elif prod_env.exists():
        load_env_file(prod_env)

    return os.environ.get("ENVIRONMENT", env_name)


# Auto-initialize on import
ACTIVE_ENV = init_environment()

