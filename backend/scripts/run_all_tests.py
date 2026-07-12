"""Run isolated regression checks without connecting to the configured MySQL database."""
import os
import subprocess
import sys


def run(label, command, env):
    print(f'\n=== {label} ===')
    result = subprocess.run(
        command,
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        env=env,
    )
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def main():
    python = sys.executable
    offline_env = os.environ.copy()
    offline_env.update({
        'AI_PROVIDER': 'mock',
        'AI_MOCK_ENABLED': 'true',
        'DEEPSEEK_API_KEY': '',
        'OCR_PROVIDER': 'mock',
    })
    run('pytest', [python, '-m', 'pytest'], offline_env)
    run('runtime smoke', [python, 'scripts/verify_runtime.py'], offline_env)
    run('statistics pure functions', [python, 'scripts/verify_stats.py'], offline_env)
    run('upload smoke', [python, 'scripts/smoke_test_upload.py'], offline_env)
    run('OCR mock pipeline', [python, 'scripts/test_ocr_pipeline.py'], offline_env)
    run('DeepSeek connection no-key guard', [python, 'scripts/test_deepseek_connection.py'], offline_env)
    run('DeepSeek structured no-key guard', [python, 'scripts/test_deepseek_structured_output.py'], offline_env)
    print('\nPASS: all offline tests completed')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
