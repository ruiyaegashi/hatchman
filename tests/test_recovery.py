"""Recovery entry points must reject missing/unsafe inputs before regeneration."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import migrate_legacy as migration


class RecoveryInputs(unittest.TestCase):
    def test_unconfigured_entry_points_fail_without_changing_tracked_outputs(self):
        paths = [ROOT / 'public/_redirects', ROOT / 'migration/inventory.json',
                 ROOT / 'reports/validation.json']
        before = [p.read_bytes() for p in paths]
        env = {k: v for k, v in os.environ.items() if k != 'HATCHMAN_BACKUP_ROOT'}
        env['PYTHONDONTWRITEBYTECODE'] = '1'
        for script in ('migrate_legacy.py', 'validate_migration.py'):
            result = subprocess.run([sys.executable, str(ROOT / 'scripts' / script)],
                                    env=env, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Set --backup-root', result.stderr)
        self.assertEqual(before, [p.read_bytes() for p in paths])

    def test_environment_and_explicit_path_with_spaces(self):
        with tempfile.TemporaryDirectory(prefix='hatchman backup ') as folder:
            root = Path(folder)
            (root / 'mysql55_20260921.zip').touch()
            with patch.dict(os.environ, {'HATCHMAN_BACKUP_ROOT': folder}):
                self.assertEqual(migration.resolve_backup_root(), root.resolve())
            with patch.dict(os.environ, {'HATCHMAN_BACKUP_ROOT': 'missing'}):
                self.assertEqual(migration.resolve_backup_root(folder), root.resolve())
            with self.assertRaisesRegex(SystemExit, 'public_html'):
                migration.resolve_backup_root(folder, require_web=True)
            (root / 'public_html').mkdir()
            self.assertEqual(migration.resolve_backup_root(folder, require_web=True), root.resolve())

    def test_repository_and_ancestors_are_not_backup_locations(self):
        for candidate in (ROOT, ROOT / 'backups', ROOT.parent):
            with self.assertRaisesRegex(SystemExit, 'outside and separate'):
                migration.resolve_backup_root(candidate)

    def test_missing_archive_is_actionable(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(SystemExit, 'mysql55_20260921.zip'):
                migration.resolve_backup_root(folder)


if __name__ == '__main__':
    unittest.main()
