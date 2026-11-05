import logging
import re

from pathlib import Path

from app.core.db import AsyncDatabase

log = logging.getLogger(__file__)


class PostgreSQLMigrationRunner:
    def __init__(self, base_dir: Path, db: AsyncDatabase):
        self.database_dir = base_dir
        self.migrations_dir = self.database_dir / "migrations"
        self.repeatable_dir = self.database_dir / "repeatable"
        self.db = db
        self.migrations = self._discover_migrations()
        self.repeatable_scripts = self._discover_repeatable_scripts()

    def _discover_migrations(self):
        """Discover all migrations and return them sorted by number"""
        pattern = r"(\d+)_(.+)\.(up|down)\.sql"
        migrations = {}

        for file_path in self.migrations_dir.glob("*.sql"):
            match = re.match(pattern, file_path.name)
            if match:
                number, name, direction = match.groups()
                number = int(number)

                if number not in migrations:
                    migrations[number] = {"name": name}

                migrations[number][direction] = file_path

        # Return sorted by migration number
        return dict(sorted(migrations.items()))

    def _discover_repeatable_scripts(self) -> list[Path]:
        if not self.repeatable_dir.exists():
            return []
        return sorted(self.repeatable_dir.glob("*.sql"))

    async def run_migration(self, migration_number, direction="up"):
        """Run a specific migration up or down"""
        if migration_number not in self.migrations:
            raise ValueError(f"Migration {migration_number} not found")

        migration = self.migrations[migration_number]
        if direction not in migration:
            raise FileNotFoundError(f"Migration {migration_number} {direction} file not found")

        migration_file = migration[direction]

        with open(migration_file, "r") as f:
            sql_content = f.read()
        await self.db.execute(sql_content)
        log.info(f"Executed {migration_file.name}")

    async def run_all_up(self):
        """Run all migrations up in forward order (001→002→003...)"""
        for migration_number in sorted(self.migrations.keys()):
            await self.run_migration(migration_number, "up")

    async def run_all_down(self):
        """Run all migrations down in reverse order (003→002→001...)"""
        for migration_number in sorted(self.migrations.keys(), reverse=True):
            await self.run_migration(migration_number, "down")

    async def run_repeatable_scripts(self):
        """Run idempotent scripts like grants, roles, extensions"""
        for script in self.repeatable_scripts:
            log.info(f"Executing repeatable script:  {script.name}")
            with open(script) as f:
                sql = f.read()
            await self.db.execute(sql)

    async def setup_database(self):
        await self.run_all_up()
        await self.run_repeatable_scripts()
