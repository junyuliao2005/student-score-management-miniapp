"""扫描 Score test 目录并生成标准导入模板。

只做本地 Excel 规则识别和转换，不写数据库，不调用后端导入接口，不调用外部 AI。
"""
import argparse
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

SERVICE_PATH = ROOT / 'backend' / 'app' / 'services' / 'excel_adapter_service.py'
spec = importlib.util.spec_from_file_location('excel_adapter_service', SERVICE_PATH)
excel_adapter_service = importlib.util.module_from_spec(spec)
sys.modules['excel_adapter_service'] = excel_adapter_service
spec.loader.exec_module(excel_adapter_service)
analyze_directory = excel_adapter_service.analyze_directory


def main():
    parser = argparse.ArgumentParser(description='转换 Score test 下的 Excel 为系统标准导入模板')
    parser.add_argument('--input-dir', default=str(ROOT / 'Score test'), help='原始 Excel 目录')
    parser.add_argument('--output-dir', default=None, help='输出目录，默认 input-dir/converted')
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir) if args.output_dir else input_dir / 'converted'

    result = analyze_directory(input_dir, output_dir)
    print(json.dumps({
        'input_dir': str(input_dir),
        'output_dir': str(output_dir),
        'summary': result['summary'],
        'output_files': result['output_files'],
    }, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
