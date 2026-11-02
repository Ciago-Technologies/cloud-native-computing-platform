import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class ProjectStructureTest(unittest.TestCase):
    def test_base_monorepo_directories_exist(self):
        required_directories = (
            "apps",
            "services",
            "desktop",
            "scheduler",
            "ai",
            "storage",
            "networking",
            "sdk",
            "helm",
            "infrastructure",
            "scripts",
            "examples",
        )

        missing = [
            directory
            for directory in required_directories
            if not (PROJECT_ROOT / directory).is_dir()
        ]

        self.assertEqual([], missing, f"Missing base directories: {missing}")

    def test_documented_language_manifests_exist(self):
        required_files = (
            "Cargo.toml",
            "apps/cloud-os-shell/Cargo.toml",
            "apps/cloud-os-shell/src/lib.rs",
            "desktop/Cargo.toml",
            "desktop/src/lib.rs",
            "scheduler/Cargo.toml",
            "scheduler/src/lib.rs",
            "storage/Cargo.toml",
            "storage/src/lib.rs",
            "sdk/rust/Cargo.toml",
            "sdk/rust/src/lib.rs",
            "go.mod",
            "apps/cli/main.go",
            "services/scheduler/service.go",
            "services/gateway/health.go",
            "services/billing/service.go",
            "services/auth/service.go",
            "services/marketplace/service.go",
            "services/workspace-orchestrator/service.go",
            "services/digital-twin/service.go",
            "services/fs-metadata/service.go",
            "networking/networking.go",
            "operators/operators.go",
            "sdk/go/sdk.go",
            "ai/pyproject.toml",
            "ai/orchestration/__init__.py",
            "ai/memory/__init__.py",
            "ai/advisors/__init__.py",
            "sdk/python/pyproject.toml",
            "apps/admin-console/package.json",
            "apps/admin-console/src/index.ts",
            "sdk/typescript/index.ts",
            "helm/Chart.yaml",
            "infrastructure/main.tf",
            "scripts/doctor.sh",
            "examples/app-manifest.yaml",
            "docs/tech-stack.md",
        )

        missing = [
            file_path
            for file_path in required_files
            if not (PROJECT_ROOT / file_path).is_file()
        ]

        self.assertEqual([], missing, f"Missing stack files: {missing}")


if __name__ == "__main__":
    unittest.main()
