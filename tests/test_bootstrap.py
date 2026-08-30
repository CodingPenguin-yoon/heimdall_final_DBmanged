from __future__ import annotations

import json
import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).parents[1]
BOOTSTRAP = REPOSITORY_ROOT / "init-managed-postgres.sh"
COMPOSE = REPOSITORY_ROOT / "compose.yaml"


class ManagedDatabaseBootstrapTests(unittest.TestCase):
    def test_bootstrap_grants_only_set_membership_for_backend_signalling(self) -> None:
        with tempfile.TemporaryDirectory() as raw_directory:
            directory = Path(raw_directory)
            capture = directory / "psql.sql"
            fake_psql = directory / "psql"
            fake_psql.write_text('#!/bin/sh\ncat > "$PSQL_CAPTURE"\n', encoding="utf-8")
            fake_psql.chmod(fake_psql.stat().st_mode | stat.S_IXUSR)
            environment = os.environ | {
                "PATH": f"{directory}:{os.environ['PATH']}",
                "POSTGRES_USER": "cluster_admin",
                "HEIMDALL_MANAGED_DB_PROVISIONER_PASSWORD": "test-provisioner-password",
                "PSQL_CAPTURE": str(capture),
            }

            subprocess.run(
                [str(BOOTSTRAP)],
                cwd=REPOSITORY_ROOT,
                env=environment,
                check=True,
            )

            sql = " ".join(capture.read_text(encoding="utf-8").split())
            self.assertIn(
                "GRANT pg_signal_backend TO heimdall_provisioner "
                "WITH INHERIT FALSE, SET TRUE, ADMIN FALSE;",
                sql,
            )

    def test_compose_reconciles_privileges_after_existing_postgres_is_healthy(self) -> None:
        environment = os.environ | {
            "HEIMDALL_MANAGED_DB_ADMIN_PASSWORD": "test-admin-password",
            "HEIMDALL_MANAGED_DB_PROVISIONER_PASSWORD": "test-provisioner-password",
        }
        result = subprocess.run(
            ["docker", "compose", "--file", str(COMPOSE), "config", "--format", "json"],
            cwd=REPOSITORY_ROOT,
            env=environment,
            check=True,
            capture_output=True,
            text=True,
        )

        services = json.loads(result.stdout)["services"]
        self.assertIn("provisioner-bootstrap", services)
        reconcile = services["provisioner-bootstrap"]
        self.assertEqual(
            reconcile["depends_on"]["postgres"]["condition"],
            "service_healthy",
        )
        self.assertEqual(reconcile["restart"], "no")


if __name__ == "__main__":
    unittest.main()
