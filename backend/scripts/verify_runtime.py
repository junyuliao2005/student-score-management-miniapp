"""
后端运行时验证脚本（SQLite 内存模式）
用法: cd backend && python scripts/verify_runtime.py

功能:
1. 使用 TestConfig（SQLite 内存数据库）创建 Flask app
2. db.create_all() 建表
3. 调用 init_db.py 中的 seed 函数初始化基础数据
4. 使用 test_client 执行完整 API 流程：
   登录 -> 创建课程 -> 创建成绩 -> 查询成绩 -> 统计刷新 -> 排名查询 -> AI mock
5. 不连接真实 MySQL，不调用真实 AI API
"""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import TestConfig
from app import create_app
from app.extensions import db
from app.models import Role, Permission, User


def main():
    results = []

    def check(name, ok, detail=''):
        status = 'PASS' if ok else 'FAIL'
        msg = f'  {status}: {name}'
        if detail:
            msg += f' ({detail})'
        print(msg)
        results.append(ok)
        if not ok:
            # 打印调用栈上下文便于调试
            import traceback
            traceback.print_exc()

    def post_json(client, url, data, token=None):
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = f'Bearer {token}'
        return client.post(url, data=json.dumps(data), headers=headers)

    def get_json(client, url, token=None):
        headers = {}
        if token:
            headers['Authorization'] = f'Bearer {token}'
        return client.get(url, headers=headers)

    def put_json(client, url, data, token=None):
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = f'Bearer {token}'
        return client.put(url, data=json.dumps(data), headers=headers)

    # ========== 基础初始化 ==========
    print('=' * 60)
    print('后端运行时验证 (SQLite 内存模式)')
    print('=' * 60)

    try:
        app = create_app(TestConfig)
        check('create_app', True)
    except Exception as e:
        check('create_app', False, str(e))
        sys.exit(1)

    with app.app_context():
        try:
            db.create_all()
            check('db.create_all', True)
        except Exception as e:
            check('db.create_all', False, str(e))
            sys.exit(1)

        try:
            from scripts.init_db import seed_roles_permissions, seed_sys_config, seed_demo_users
            seed_roles_permissions(app)
            role_count = Role.query.count()
            perm_count = Permission.query.count()
            check('seed roles/permissions', role_count >= 3 and perm_count >= 19,
                  f'roles={role_count}, perms={perm_count}')
        except Exception as e:
            check('seed roles/permissions', False, str(e))

        try:
            seed_sys_config(app)
            from app.models import SysConfig
            config_count = SysConfig.query.count()
            check('seed sys_config', config_count >= 1, f'configs={config_count}')
        except Exception as e:
            check('seed sys_config', False, str(e))

        try:
            seed_demo_users(app)
            user_count = User.query.count()
            check('seed users', user_count >= 1, f'users={user_count}')
        except Exception as e:
            check('seed users', False, str(e))

        # ========== API 级别测试 ==========
        with app.test_client() as client:

            # --- health ---
            try:
                resp = client.get('/api/health')
                data = resp.get_json()
                check('GET /api/health', resp.status_code == 200 and data.get('code') == 0,
                      f'code={data.get("code")}')
            except Exception as e:
                check('GET /api/health', False, str(e))

            # --- 登录 admin01 ---
            admin_token = None
            try:
                resp = post_json(client, '/api/auth/login',
                                  {'username': 'admin01', 'password': '123456'})
                data = resp.get_json()
                admin_token = data.get('data', {}).get('token') if data else None
                check('POST /api/auth/login (admin)', admin_token is not None,
                      f'code={data.get("code")}')
            except Exception as e:
                check('POST /api/auth/login (admin)', False, str(e))

            # --- 登录 teacher01 ---
            teacher_token = None
            try:
                resp = post_json(client, '/api/auth/login',
                                  {'username': 'teacher01', 'password': '123456'})
                data = resp.get_json()
                teacher_token = data.get('data', {}).get('token') if data else None
                check('POST /api/auth/login (teacher)', teacher_token is not None,
                      f'code={data.get("code")}')
            except Exception as e:
                check('POST /api/auth/login (teacher)', False, str(e))

            # --- 登录 student01 ---
            student_token = None
            try:
                resp = post_json(client, '/api/auth/login',
                                  {'username': 'student01', 'password': '123456'})
                data = resp.get_json()
                student_token = data.get('data', {}).get('token') if data else None
                check('POST /api/auth/login (student)', student_token is not None,
                      f'code={data.get("code")}')
            except Exception as e:
                check('POST /api/auth/login (student)', False, str(e))

            # --- 创建课程 (admin) ---
            try:
                resp = post_json(client, '/api/courses', {
                    'course_id': 'MATH01',
                    'course_name': '数学',
                    'teacher_id': 'T001',
                    'term': '2025-2026-2',
                    'credit': 4,
                }, token=admin_token)
                data = resp.get_json()
                check('POST /api/courses (admin)', data.get('code') == 0,
                      f'code={data.get("code")}, msg={data.get("message")}')
            except Exception as e:
                check('POST /api/courses (admin)', False, str(e))

            # --- 创建成绩 (teacher) ---
            try:
                resp = put_json(client, '/api/admin/teacher-bindings/T001', {
                    'class_names': ['2025级1班'],
                    'course_ids': ['MATH01'],
                }, token=admin_token)
                data = resp.get_json()
                check('PUT /api/admin/teacher-bindings/T001', data.get('code') == 0,
                      f'code={data.get("code")}')
            except Exception as e:
                check('PUT /api/admin/teacher-bindings/T001', False, str(e))

            # --- 创建成绩 (teacher) ---
            try:
                resp = post_json(client, '/api/scores', {
                    'student_id': 'S001',
                    'course_id': 'MATH01',
                    'score': 90,
                    'exam_date': '2026-04-10',
                    'exam_batch': '期中',
                }, token=teacher_token)
                data = resp.get_json()
                check('POST /api/scores (teacher)', data.get('code') == 0,
                      f'code={data.get("code")}, msg={data.get("message")}')
            except Exception as e:
                check('POST /api/scores (teacher)', False, str(e))

            # --- 学生查询个人成绩 ---
            try:
                resp = get_json(client, '/api/scores/my', token=student_token)
                data = resp.get_json()
                scores = data.get('data', {}).get('scores', [])
                check('GET /api/scores/my before publish', data.get('code') == 0 and not scores,
                      f'code={data.get("code")}, scores={len(scores)}')
            except Exception as e:
                check('GET /api/scores/my before publish', False, str(e))

            # --- 创建并发布考试成绩可见范围 ---
            publish_id = None
            try:
                resp = post_json(client, '/api/exam-publish', {
                    'exam_name': '期中成绩发布',
                    'term': '2025-2026-2',
                    'exam_batch': '期中',
                    'class_name': '2025级1班',
                    'require_parent_signature': False,
                }, token=teacher_token)
                data = resp.get_json()
                publish_id = data.get('data', {}).get('id')
                check('POST /api/exam-publish (teacher)', bool(publish_id),
                      f'code={data.get("code")}')
                resp = post_json(client, f'/api/exam-publish/{publish_id}/publish', {}, token=teacher_token)
                data = resp.get_json()
                check('POST /api/exam-publish/<id>/publish', data.get('code') == 0,
                      f'code={data.get("code")}')
            except Exception as e:
                check('publish score visibility', False, str(e))

            try:
                resp = get_json(client, '/api/scores/my', token=student_token)
                data = resp.get_json()
                scores = data.get('data', {}).get('scores', [])
                check('GET /api/scores/my after publish', data.get('code') == 0 and len(scores) == 1,
                      f'code={data.get("code")}, scores={len(scores)}')
            except Exception as e:
                check('GET /api/scores/my after publish', False, str(e))

            # --- 触发统计刷新 (teacher) ---
            try:
                # 清除 config_loader 缓存，模拟真实跨请求场景
                from app.services import config_loader
                config_loader.clear_cache()

                resp = post_json(client, '/api/stats/evaluate', {
                    'term': '2025-2026-2',
                    'class_name': '2025级1班',
                }, token=teacher_token)
                data = resp.get_json()
                check('POST /api/stats/evaluate (teacher)', data.get('code') == 0,
                      f'code={data.get("code")}, msg={data.get("message")}')
            except Exception as e:
                check('POST /api/stats/evaluate (teacher)', False, str(e))

            # --- 查询排名 (teacher) ---
            try:
                resp = get_json(client,
                                '/api/stats/rankings?term=2025-2026-2&class_name=2025级1班',
                                token=teacher_token)
                data = resp.get_json()
                check('GET /api/stats/rankings (teacher)', data.get('code') == 0,
                      f'code={data.get("code")}')
            except Exception as e:
                check('GET /api/stats/rankings (teacher)', False, str(e))

            # --- AI mock: 学生学习建议 (teacher) ---
            try:
                config_loader.clear_cache()
                resp = post_json(client, '/api/ai/student-advice', {
                    'student_id': 'S001',
                    'term': '2025-2026-2',
                }, token=teacher_token)
                data = resp.get_json()
                ai_ok = data.get('code') == 0
                ai_data = data.get('data', {}) if data else {}
                is_mock = ai_data.get('is_mock', False)
                provider = ai_data.get('provider', '')
                check('POST /api/ai/student-advice (mock)',
                      ai_ok and is_mock and provider == 'mock',
                      f'code={data.get("code")}, is_mock={is_mock}, provider={provider}')
            except Exception as e:
                check('POST /api/ai/student-advice (mock)', False, str(e))

    # ========== 汇总 ==========
    print('=' * 60)
    passed = sum(results)
    total = len(results)
    if all(results):
        print(f'全部通过: {passed}/{total}')
    else:
        failed = total - passed
        print(f'通过 {passed}/{total}，有 {failed} 项失败')
        sys.exit(1)
    print('=' * 60)


if __name__ == '__main__':
    main()
