"""Build validated full and public release archives without staging real data."""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[2]
DELIVERABLES = ROOT / 'deliverables'
FULL_NAME = '学生成绩管理小程序_最终发布候选版.zip'
PUBLIC_NAME = '学生成绩管理小程序_GitHub公开版.zip'

SKIP_DIR_NAMES = {
    '.git', '.pytest_cache', '.pytest-tmp', '.runtime', '.tmp', '__pycache__',
    'deliverables', 'htmlcov', 'local_backups', 'logs', 'node_modules',
    'score test', 'temp', 'tmp', 'uploads',
}
SKIP_FILE_NAMES = {
    '.coverage', 'project.private.config.json', 'desktop.ini', 'thumbs.db',
}
SAFE_ENV_FILES = {'.env.example', '.env.cloud.example', '.env.docker.example'}
SKIP_SUFFIXES = {
    '.bak', '.backup', '.db', '.dump', '.log', '.pyc', '.pyo', '.sqlite',
    '.sqlite3', '.xls', '.xlsx', '.zip',
}
PUBLIC_BINARY_SKIP_SUFFIXES = {'.docx', '.pdf'}
FULL_REPORT_EXCLUDES = {
    'docs/CODEX_AUTONOMOUS_PROGRESS.md',
    'docs/最终发布报告.md',
}
PUBLIC_REPORT_EXCLUDES = {
    'docs/CODEX_AUTONOMOUS_PROGRESS.md',
    'docs/DeepSeek真实连接验证报告.md',
    'docs/GIT待执行操作.md',
    'docs/OCR真实环境验证报告.md',
    'docs/P3-P5最终验证与交付报告.md',
    'docs/NEXT_TASKS.md',
    'docs/当前项目真实状态清单.md',
    'docs/本地依赖安装报告.md',
    'docs/本地数据库迁移报告.md',
    'docs/本地端到端验收报告.md',
    'docs/预发布验收报告.md',
    'docs/最终发布报告.md',
    'docs/下一会话续跑提示词.md',
    'docs/main-fixed.tex',
}
TEXT_SUFFIXES = {
    '', '.bat', '.conf', '.css', '.dockerignore', '.env', '.example', '.gitignore',
    '.html', '.ini', '.js', '.json', '.md', '.ps1', '.py', '.sql', '.svg',
    '.tex', '.txt', '.wxml', '.wxss', '.yaml', '.yml',
}

PUBLIC_REPLACEMENTS = {
    'S001': 'S001',
    '演示学生': '演示学生',
    'replace-with-cloud-env-id': 'replace-with-cloud-env-id',
    'replace-with-your-cloud-domain.example': 'replace-with-your-cloud-domain.example',
    'replace-with-service-name': 'replace-with-service-name',
    str(ROOT): '<PROJECT_ROOT>',
    str(ROOT).replace('\\', '/'): '<PROJECT_ROOT>',
}

SECRET_PATTERNS = {
    'private_key': re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
    'provider_key': re.compile(r'\b(?:sk|ds)-[A-Za-z0-9_-]{20,}\b'),
    'jwt': re.compile(r'\beyJ[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{12,}\b'),
    'filled_env_secret': re.compile(
        r'(?im)^\s*(?:DEEPSEEK_API_KEY|AI_API_KEY|AI_VISION_API_KEY|DB_PASSWORD|'
        r'JWT_SECRET_KEY|SECRET_KEY)[ \t]*=[ \t]*(?![ \t]*(?:$|replace-|your[-_]|<|填写|在此填写|你的))([^\s#]{8,})[ \t]*$'
    ),
}
PUBLIC_PRIVATE_PATTERNS = {
    'real_student_id': re.compile(r'\bK12S\d{6}\b'),
    'real_student_name': re.compile(r'演示学生'),
    'real_cloud_env': re.compile(r'replace-with-cloud-env-id'),
    'real_cloud_service': re.compile(r'replace-with-service-name'),
    'real_cloud_domain': re.compile(r'sh\.run\.tcloudbase\.com'),
    'real_appid': re.compile(r'"appid"\s*:\s*"(?!touristappid|replace-with-)[^"]+"'),
}


def _is_skipped_dir(name: str) -> bool:
    lowered = name.lower()
    return lowered in SKIP_DIR_NAMES or lowered.startswith('.venv')


def _should_include(path: Path, public: bool) -> bool:
    rel = path.relative_to(ROOT).as_posix()
    name = path.name.lower()
    if name in SKIP_FILE_NAMES:
        return False
    if name.startswith('.env') and name not in SAFE_ENV_FILES:
        return False
    if path.suffix.lower() in SKIP_SUFFIXES:
        return False
    if public and path.suffix.lower() in PUBLIC_BINARY_SKIP_SUFFIXES:
        return False
    if rel in FULL_REPORT_EXCLUDES:
        return False
    if public and rel in PUBLIC_REPORT_EXCLUDES:
        return False
    return True


def _iter_source_files(public: bool):
    for base, dirs, files in os.walk(ROOT, topdown=True):
        dirs[:] = sorted(d for d in dirs if not _is_skipped_dir(d))
        base_path = Path(base)
        for name in sorted(files):
            path = base_path / name
            if _should_include(path, public):
                yield path


def _is_text(path: Path, data: bytes) -> bool:
    if path.suffix.lower() in TEXT_SUFFIXES or path.name in {'.gitignore', '.dockerignore'}:
        return True
    return b'\x00' not in data[:4096]


def _public_transform(path: Path, data: bytes) -> bytes:
    if not _is_text(path, data):
        return data
    try:
        text = data.decode('utf-8-sig')
    except UnicodeDecodeError:
        return data
    for old, new in PUBLIC_REPLACEMENTS.items():
        text = text.replace(old, new)
    text = re.sub(r'\bK12S\d{6}\b', 'S001', text)
    rel = path.relative_to(ROOT).as_posix()
    if rel in {'project.config.json', 'miniprogram/project.config.json'}:
        try:
            config = json.loads(text)
            config['appid'] = 'touristappid'
            text = json.dumps(config, ensure_ascii=False, indent=2) + '\n'
        except json.JSONDecodeError:
            text = re.sub(r'("appid"\s*:\s*)"[^"]+"', r'\1"touristappid"', text)
    return text.encode('utf-8')


def _generated_public_files():
    notice = """# GitHub 公开版说明

本压缩包由发布脚本从本地候选版自动生成，已排除真实数据库、备份、Excel、日志、上传文件、私有微信配置和本地验收报告，并替换真实学生快捷账号与云环境标识。

- 所有演示账号、姓名、班级和成绩均为虚构测试数据。
- `project.config.json` 使用 `touristappid`，部署前请在本地私有配置中填写自己的 AppID。
- `.env.example` 只含占位符；真实密码、JWT Secret 和 AI Key 必须通过未跟踪的环境变量注入。
- 项目截图需由维护者在微信开发者工具或真机中使用虚构数据重新截取，禁止上传真实学生成绩截图。
"""
    screenshots = """# 项目截图目录

当前自动化环境无法写入微信开发者工具的用户目录，因此没有伪造界面截图。公开发布前请使用虚构演示数据补充：登录页、教师统计、学生已发布成绩、家长确认、OCR 预览和 AI 结果六张截图，并逐张检查姓名、学号、成绩、trace_id 和云环境信息已脱敏。
"""
    return {
        'PUBLIC_RELEASE_NOTICE.md': notice.encode('utf-8'),
        'docs/screenshots/README.md': screenshots.encode('utf-8'),
    }


def _scan_text(name: str, data: bytes, patterns: dict[str, re.Pattern]):
    try:
        text = data.decode('utf-8-sig')
    except UnicodeDecodeError:
        return []
    hits = []
    for label, pattern in patterns.items():
        if label == 'filled_env_secret' and not PurePosixPath(name).name.startswith('.env'):
            continue
        if pattern.search(text):
            hits.append(f'{name}:{label}')
    return hits


def _banned_archive_name(name: str) -> bool:
    path = PurePosixPath(name)
    lowered_parts = [part.lower() for part in path.parts]
    if any(part in SKIP_DIR_NAMES or part.startswith('.venv') for part in lowered_parts):
        return True
    filename = path.name.lower()
    if filename in SKIP_FILE_NAMES or (filename.startswith('.env') and filename not in SAFE_ENV_FILES):
        return True
    return path.suffix.lower() in SKIP_SUFFIXES


def _validate_archive(path: Path, public: bool):
    secret_hits = []
    privacy_hits = []
    with zipfile.ZipFile(path, 'r') as archive:
        corrupt = archive.testzip()
        names = archive.namelist()
        banned = [name for name in names if _banned_archive_name(name)]
        for name in names:
            data = archive.read(name)
            secret_hits.extend(_scan_text(name, data, SECRET_PATTERNS))
            if public:
                privacy_hits.extend(_scan_text(name, data, PUBLIC_PRIVATE_PATTERNS))
    if corrupt or banned or secret_hits or privacy_hits:
        raise RuntimeError(json.dumps({
            'corrupt': corrupt,
            'banned': banned[:20],
            'secret_hits': secret_hits[:20],
            'privacy_hits': privacy_hits[:20],
        }, ensure_ascii=False))
    return {
        'crc': 'PASS',
        'file_count': len(names),
        'banned_count': len(banned),
        'secret_hits': len(secret_hits),
        'privacy_hits': len(privacy_hits),
    }


def _build(target: Path, public: bool):
    if target.exists():
        raise FileExistsError(f'Refusing to overwrite existing archive: {target}')
    DELIVERABLES.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix='.release-', suffix='.zip', dir=DELIVERABLES)
    os.close(fd)
    temp_path = Path(temp_name)
    try:
        with zipfile.ZipFile(temp_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            count = 0
            for path in _iter_source_files(public):
                data = path.read_bytes()
                if public:
                    data = _public_transform(path, data)
                archive.writestr(path.relative_to(ROOT).as_posix(), data)
                count += 1
            if public:
                for name, data in _generated_public_files().items():
                    archive.writestr(name, data)
                    count += 1
            manifest = {
                'release_kind': 'github-public' if public else 'full-candidate',
                'generated_at': datetime.now(timezone.utc).isoformat(),
                'source_file_count': count,
                'contains_real_database_or_backup': False,
                'public_data_sanitized': public,
                'screenshots': 'manual_capture_required' if public else 'not_embedded',
            }
            archive.writestr('release-manifest.json', json.dumps(manifest, ensure_ascii=False, indent=2))
        os.replace(temp_path, target)
        checks = _validate_archive(target, public)
        checks.update({
            'path': str(target),
            'size_bytes': target.stat().st_size,
            'sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
        })
        return checks
    except Exception:
        temp_path.unlink(missing_ok=True)
        if target.exists():
            target.unlink()
        raise


def main():
    results = [
        _build(DELIVERABLES / FULL_NAME, public=False),
        _build(DELIVERABLES / PUBLIC_NAME, public=True),
    ]
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
