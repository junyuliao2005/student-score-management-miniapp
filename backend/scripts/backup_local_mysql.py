"""Create a local-only MySQL backup without exposing credentials on the command line."""
import argparse
import hashlib
import os
import re
import shutil
import subprocess
import sys
import uuid
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv


BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent
LOCAL_HOSTS = {'127.0.0.1', 'localhost', '::1'}
COMMON_MYSQLDUMP_PATHS = (
    Path(r'C:\Program Files\MySQL\MySQL Server 8.4\bin\mysqldump.exe'),
    Path(r'C:\Program Files\MySQL\MySQL Server 8.0\bin\mysqldump.exe'),
)


def main():
    parser = argparse.ArgumentParser(description='Back up the configured local MySQL database.')
    parser.add_argument('--output-dir', default=str(PROJECT_ROOT / 'local_backups'))
    args = parser.parse_args()

    load_dotenv(BACKEND_ROOT / '.env', override=False)
    host = os.getenv('DB_HOST', '').strip().lower()
    port = int(os.getenv('DB_PORT', '3306'))
    user = os.getenv('DB_USER', '').strip()
    password = os.getenv('DB_PASSWORD', '')
    database = os.getenv('DB_NAME', '').strip()

    if host not in LOCAL_HOSTS:
        raise SystemExit('REFUSED: DB_HOST is not a confirmed local host')
    if not user or not database or not re.fullmatch(r'[A-Za-z0-9_]+', database):
        raise SystemExit('REFUSED: local database configuration is incomplete or unsafe')

    mysqldump = _find_mysqldump()
    if not mysqldump:
        raise SystemExit('SKIPPED: mysqldump was not found; set MYSQLDUMP_PATH')

    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    runtime_dir = PROJECT_ROOT / '.tmp'
    runtime_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    output_path = output_dir / f'{database}-{timestamp}.sql'
    option_path = runtime_dir / f'mysql-client-{uuid.uuid4().hex}.cnf'

    option_path.write_text(
        '[client]\n'
        f'host={_option_value(host)}\n'
        f'port={port}\n'
        f'user={_option_value(user)}\n'
        f'password={_option_value(password)}\n'
        'default-character-set=utf8mb4\n',
        encoding='utf-8',
    )
    command = [
        str(mysqldump),
        f'--defaults-extra-file={option_path}',
        '--single-transaction',
        '--quick',
        '--routines',
        '--triggers',
        '--events',
        '--hex-blob',
        '--set-gtid-purged=OFF',
        '--no-tablespaces',
        database,
    ]
    try:
        with output_path.open('wb') as output:
            result = subprocess.run(
                command,
                stdout=output,
                stderr=subprocess.PIPE,
                timeout=600,
                check=False,
            )
        if result.returncode != 0:
            output_path.unlink(missing_ok=True)
            message = result.stderr.decode('utf-8', errors='replace').strip()
            raise SystemExit(f'FAILED: mysqldump returned {result.returncode}: {_sanitize(message)}')
        size = output_path.stat().st_size
        if size < 1024:
            output_path.unlink(missing_ok=True)
            raise SystemExit('FAILED: backup output was unexpectedly small')
        digest = _sha256(output_path)
        print(f'BACKUP_PATH={output_path}')
        print(f'BACKUP_BYTES={size}')
        print(f'BACKUP_SHA256={digest}')
        return 0
    finally:
        option_path.unlink(missing_ok=True)


def _find_mysqldump():
    configured = os.getenv('MYSQLDUMP_PATH', '').strip()
    candidates = [Path(configured)] if configured else []
    discovered = shutil.which('mysqldump')
    if discovered:
        candidates.append(Path(discovered))
    candidates.extend(COMMON_MYSQLDUMP_PATHS)
    return next((path for path in candidates if path.is_file()), None)


def _option_value(value):
    escaped = str(value).replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
    return f'"{escaped}"'


def _sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _sanitize(message):
    password = os.getenv('DB_PASSWORD', '')
    return message.replace(password, '***') if password else message


if __name__ == '__main__':
    raise SystemExit(main())
