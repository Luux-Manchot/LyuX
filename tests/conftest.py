import sys
import os
import csv
import importlib.util
from pathlib import Path
import pytest
import yaml
from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parent.parent

def load_dynamic_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(path.parent))
    spec.loader.exec_module(module)
    return module

@pytest.fixture(scope="session")
def project_root() -> Path:
    return ROOT_DIR

@pytest.fixture(scope="session")
def server_api_module():
    api_path = ROOT_DIR / "projects" / "lyux-server-api" / "src" / "main.py"
    return load_dynamic_module("e2e_server_api", api_path)

@pytest.fixture(scope="session")
def api_client(server_api_module):
    return TestClient(server_api_module.app)

@pytest.fixture(scope="session")
def docker_compose_data() -> dict:
    dc_path = ROOT_DIR / "projects" / "lyux-server-infra" / "docker-compose.yml"
    assert dc_path.exists(), f"Fichier docker-compose introuvable : {dc_path}"
    with open(dc_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

@pytest.fixture(scope="session")
def ansible_inventory_data() -> dict:
    inv_path = ROOT_DIR / "projects" / "lyux-ansible" / "inventory" / "hosts.yml"
    assert inv_path.exists(), f"Inventaire Ansible introuvable : {inv_path}"
    with open(inv_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

@pytest.fixture(scope="session")
def test_users_csv() -> list:
    csv_path = ROOT_DIR / "projects" / "lyux-server-infra" / "configs" / "utilisateurs-test.csv"
    assert csv_path.exists(), f"Fichier CSV utilisateurs introuvable : {csv_path}"
    users = []
    with open(csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            users.append(row)
    return users
