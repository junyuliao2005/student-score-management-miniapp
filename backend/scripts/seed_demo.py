"""
演示数据填充脚本
用法: cd backend && python scripts/seed_demo.py

功能:
1. 创建 1 个管理员、2 个教师、20 个学生
2. 创建 5 门课程：语文、数学、英语、物理、计算机基础
3. 为学生生成期中成绩（含边界值和特殊场景）
4. 自动触发统计刷新（总分/平均分/排名/等级/评语）
"""

import sys
import os
from decimal import Decimal
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.models import User, Role, UserRole, Course, Score
from app.utils.hash_util import hash_password
from app.services import stats_service


def main():
    app = create_app()
    with app.app_context():
        print('=' * 60)
        print('填充演示数据')
        print('=' * 60)

        default_pw = hash_password('123456')

        # ========== 管理员 ==========
        if not User.query.filter_by(user_id='A001').first():
            user = User(user_id='A001', username='admin01', password_hash=default_pw,
                        real_name='系统管理员', status=1)
            db.session.add(user)
            db.session.flush()
            role = Role.query.filter_by(role_name='admin').first()
            if role:
                db.session.add(UserRole(user_id='A001', role_id=role.role_id))
        print('[OK] 管理员账号就绪')

        # ========== 教师 ==========
        teachers = [
            ('T001', 'teacher01', '张老师'),
            ('T002', 'teacher02', '李老师'),
        ]
        for uid, uname, rname in teachers:
            if not User.query.filter_by(user_id=uid).first():
                user = User(user_id=uid, username=uname, password_hash=default_pw,
                            real_name=rname, status=1)
                db.session.add(user)
                db.session.flush()
                role = Role.query.filter_by(role_name='teacher').first()
                if role:
                    db.session.add(UserRole(user_id=uid, role_id=role.role_id))
        print('[OK] 教师账号就绪')

        # ========== 学生（20人） ==========
        students_data = [
            # (user_id, username, real_name, class_name)
            # --- 2025级1班 ---
            ('S001', 'student01', '赵一', '2025级1班'),
            ('S002', 'student02', '钱二', '2025级1班'),
            ('S003', 'student03', '孙三', '2025级1班'),
            ('S004', 'student04', '李四', '2025级1班'),
            ('S005', 'student05', '周五', '2025级1班'),
            ('S006', 'student06', '吴六', '2025级1班'),
            ('S007', 'student07', '郑七', '2025级1班'),
            ('S008', 'student08', '王八', '2025级1班'),
            ('S009', 'student09', '冯九', '2025级1班'),
            ('S010', 'student10', '陈十', '2025级1班'),
            ('S011', 'student11', '褚十一', '2025级1班'),
            ('S012', 'student12', '卫十二', '2025级1班'),
            # --- 2025级2班 ---
            ('S013', 'student13', '蒋十三', '2025级2班'),
            ('S014', 'student14', '沈十四', '2025级2班'),
            ('S015', 'student15', '韩十五', '2025级2班'),
            ('S016', 'student16', '杨十六', '2025级2班'),
            ('S017', 'student17', '朱十七', '2025级2班'),
            ('S018', 'student18', '秦十八', '2025级2班'),
            ('S019', 'student19', '尤十九', '2025级2班'),
            ('S020', 'student20', '许二十', '2025级2班'),
        ]
        for uid, uname, rname, cls in students_data:
            if not User.query.filter_by(user_id=uid).first():
                user = User(user_id=uid, username=uname, password_hash=default_pw,
                            real_name=rname, class_name=cls, status=1)
                db.session.add(user)
                db.session.flush()
                role = Role.query.filter_by(role_name='student').first()
                if role:
                    db.session.add(UserRole(user_id=uid, role_id=role.role_id))
        db.session.commit()
        print('[OK] 学生账号就绪（20人，2个班）')

        # ========== 课程（5门） ==========
        courses_data = [
            ('CHN01', '语文', 'T001', '2025-2026-2', '3.0'),
            ('MATH01', '数学', 'T001', '2025-2026-2', '4.0'),
            ('ENG01', '英语', 'T002', '2025-2026-2', '3.0'),
            ('PHY01', '物理', 'T002', '2025-2026-2', '3.0'),
            ('CS01', '计算机基础', 'T001', '2025-2026-2', '2.0'),
        ]
        for cid, cname, tid, term, credit in courses_data:
            if not Course.query.filter_by(course_id=cid).first():
                db.session.add(Course(
                    course_id=cid, course_name=cname, teacher_id=tid,
                    term=term, credit=Decimal(credit), status=1
                ))
        db.session.commit()
        print('[OK] 课程就绪（5门：语文、数学、英语、物理、计算机基础）')

        # ========== 成绩数据 ==========
        # 设计说明：
        # S001: 全科高分 -> 优秀
        # S002: 全科中等 -> 中等
        # S003: 偏科（数学高/英语低）-> 偏科预警
        # S004: 全科低分 -> 低分预警
        # S005: 与 S001 完全同分 -> 验证排名 1,1,3
        # S006: 边界值 59.99 -> 不及格
        # S007: 边界值 60 -> 及格
        # S008: 边界值 89.99 -> 良好
        # S009: 边界值 90 -> 优秀
        # S010: 满分 100 -> 优秀
        # S011: 文科型（语文英语高/数学物理低）
        # S012: 理科型（数学物理高/语文英语低）
        # S013-S020: 2班学生，覆盖不同层次

        scores_data = [
            # (student_id, course_id, score, exam_date, exam_batch)

            # --- S001: 全科高分学生 ---
            ('S001', 'CHN01', 93, '2026-04-10', '期中'),
            ('S001', 'MATH01', 95, '2026-04-10', '期中'),
            ('S001', 'ENG01', 92, '2026-04-11', '期中'),
            ('S001', 'PHY01', 96, '2026-04-11', '期中'),
            ('S001', 'CS01', 98, '2026-04-12', '期中'),

            # --- S002: 全科中等学生 ---
            ('S002', 'CHN01', 74, '2026-04-10', '期中'),
            ('S002', 'MATH01', 75, '2026-04-10', '期中'),
            ('S002', 'ENG01', 72, '2026-04-11', '期中'),
            ('S002', 'PHY01', 70, '2026-04-11', '期中'),
            ('S002', 'CS01', 78, '2026-04-12', '期中'),

            # --- S003: 偏科学生（数学高/英语低）---
            ('S003', 'CHN01', 80, '2026-04-10', '期中'),
            ('S003', 'MATH01', 95, '2026-04-10', '期中'),
            ('S003', 'ENG01', 45, '2026-04-11', '期中'),
            ('S003', 'PHY01', 88, '2026-04-11', '期中'),
            ('S003', 'CS01', 85, '2026-04-12', '期中'),

            # --- S004: 全科低分学生 ---
            ('S004', 'CHN01', 48, '2026-04-10', '期中'),
            ('S004', 'MATH01', 42, '2026-04-10', '期中'),
            ('S004', 'ENG01', 38, '2026-04-11', '期中'),
            ('S004', 'PHY01', 50, '2026-04-11', '期中'),
            ('S004', 'CS01', 55, '2026-04-12', '期中'),

            # --- S005: 与 S001 完全同分（验证排名 1,1,3）---
            ('S005', 'CHN01', 93, '2026-04-10', '期中'),
            ('S005', 'MATH01', 95, '2026-04-10', '期中'),
            ('S005', 'ENG01', 92, '2026-04-11', '期中'),
            ('S005', 'PHY01', 96, '2026-04-11', '期中'),
            ('S005', 'CS01', 98, '2026-04-12', '期中'),

            # --- S006: 边界值 59.99 ---
            ('S006', 'CHN01', 62, '2026-04-10', '期中'),
            ('S006', 'MATH01', 59.99, '2026-04-10', '期中'),
            ('S006', 'ENG01', 65, '2026-04-11', '期中'),
            ('S006', 'PHY01', 58, '2026-04-11', '期中'),
            ('S006', 'CS01', 70, '2026-04-12', '期中'),

            # --- S007: 边界值 60 ---
            ('S007', 'CHN01', 65, '2026-04-10', '期中'),
            ('S007', 'MATH01', 60, '2026-04-10', '期中'),
            ('S007', 'ENG01', 68, '2026-04-11', '期中'),
            ('S007', 'PHY01', 63, '2026-04-11', '期中'),
            ('S007', 'CS01', 72, '2026-04-12', '期中'),

            # --- S008: 边界值 89.99 ---
            ('S008', 'CHN01', 85, '2026-04-10', '期中'),
            ('S008', 'MATH01', 89.99, '2026-04-10', '期中'),
            ('S008', 'ENG01', 85, '2026-04-11', '期中'),
            ('S008', 'PHY01', 82, '2026-04-11', '期中'),
            ('S008', 'CS01', 88, '2026-04-12', '期中'),

            # --- S009: 边界值 90 ---
            ('S009', 'CHN01', 88, '2026-04-10', '期中'),
            ('S009', 'MATH01', 90, '2026-04-10', '期中'),
            ('S009', 'ENG01', 88, '2026-04-11', '期中'),
            ('S009', 'PHY01', 92, '2026-04-11', '期中'),
            ('S009', 'CS01', 92, '2026-04-12', '期中'),

            # --- S010: 满分 100 ---
            ('S010', 'CHN01', 100, '2026-04-10', '期中'),
            ('S010', 'MATH01', 100, '2026-04-10', '期中'),
            ('S010', 'ENG01', 100, '2026-04-11', '期中'),
            ('S010', 'PHY01', 100, '2026-04-11', '期中'),
            ('S010', 'CS01', 100, '2026-04-12', '期中'),

            # --- S011: 文科型（语文英语高/数学物理低）---
            ('S011', 'CHN01', 92, '2026-04-10', '期中'),
            ('S011', 'MATH01', 55, '2026-04-10', '期中'),
            ('S011', 'ENG01', 90, '2026-04-11', '期中'),
            ('S011', 'PHY01', 48, '2026-04-11', '期中'),
            ('S011', 'CS01', 75, '2026-04-12', '期中'),

            # --- S012: 理科型（数学物理高/语文英语低）---
            ('S012', 'CHN01', 58, '2026-04-10', '期中'),
            ('S012', 'MATH01', 96, '2026-04-10', '期中'),
            ('S012', 'ENG01', 52, '2026-04-11', '期中'),
            ('S012', 'PHY01', 94, '2026-04-11', '期中'),
            ('S012', 'CS01', 90, '2026-04-12', '期中'),

            # --- 2025级2班学生 ---

            # S013: 优秀学生
            ('S013', 'CHN01', 88, '2026-04-10', '期中'),
            ('S013', 'MATH01', 92, '2026-04-10', '期中'),
            ('S013', 'ENG01', 85, '2026-04-11', '期中'),
            ('S013', 'PHY01', 90, '2026-04-11', '期中'),
            ('S013', 'CS01', 91, '2026-04-12', '期中'),

            # S014: 良好学生
            ('S014', 'CHN01', 82, '2026-04-10', '期中'),
            ('S014', 'MATH01', 85, '2026-04-10', '期中'),
            ('S014', 'ENG01', 80, '2026-04-11', '期中'),
            ('S014', 'PHY01', 78, '2026-04-11', '期中'),
            ('S014', 'CS01', 83, '2026-04-12', '期中'),

            # S015: 中等学生
            ('S015', 'CHN01', 72, '2026-04-10', '期中'),
            ('S015', 'MATH01', 68, '2026-04-10', '期中'),
            ('S015', 'ENG01', 75, '2026-04-11', '期中'),
            ('S015', 'PHY01', 70, '2026-04-11', '期中'),
            ('S015', 'CS01', 74, '2026-04-12', '期中'),

            # S016: 及格线学生
            ('S016', 'CHN01', 62, '2026-04-10', '期中'),
            ('S016', 'MATH01', 60, '2026-04-10', '期中'),
            ('S016', 'ENG01', 61, '2026-04-11', '期中'),
            ('S016', 'PHY01', 63, '2026-04-11', '期中'),
            ('S016', 'CS01', 65, '2026-04-12', '期中'),

            # S017: 偏科学生（物理极高/英语极低）
            ('S017', 'CHN01', 70, '2026-04-10', '期中'),
            ('S017', 'MATH01', 78, '2026-04-10', '期中'),
            ('S017', 'ENG01', 40, '2026-04-11', '期中'),
            ('S017', 'PHY01', 98, '2026-04-11', '期中'),
            ('S017', 'CS01', 82, '2026-04-12', '期中'),

            # S018: 低分学生
            ('S018', 'CHN01', 45, '2026-04-10', '期中'),
            ('S018', 'MATH01', 35, '2026-04-10', '期中'),
            ('S018', 'ENG01', 42, '2026-04-11', '期中'),
            ('S018', 'PHY01', 40, '2026-04-11', '期中'),
            ('S018', 'CS01', 50, '2026-04-12', '期中'),

            # S019: 边界综合（数学59.99/物理90）
            ('S019', 'CHN01', 66, '2026-04-10', '期中'),
            ('S019', 'MATH01', 59.99, '2026-04-10', '期中'),
            ('S019', 'ENG01', 70, '2026-04-11', '期中'),
            ('S019', 'PHY01', 90, '2026-04-11', '期中'),
            ('S019', 'CS01', 72, '2026-04-12', '期中'),

            # S020: 中上学生
            ('S020', 'CHN01', 78, '2026-04-10', '期中'),
            ('S020', 'MATH01', 82, '2026-04-10', '期中'),
            ('S020', 'ENG01', 76, '2026-04-11', '期中'),
            ('S020', 'PHY01', 80, '2026-04-11', '期中'),
            ('S020', 'CS01', 85, '2026-04-12', '期中'),
        ]

        for sid, cid, score, edate, batch in scores_data:
            existing = Score.query.filter_by(
                student_id=sid, course_id=cid, exam_batch=batch, status=1
            ).first()
            if not existing:
                db.session.add(Score(
                    student_id=sid, course_id=cid,
                    score=Decimal(str(score)),
                    exam_date=datetime.strptime(edate, "%Y-%m-%d").date(),
                    exam_batch=batch,
                    status=1,
                    stat_version=0,
                ))
        db.session.commit()
        print('[OK] 成绩数据就绪（100条，覆盖全部场景）')

        # ========== 触发统计刷新 ==========
        print('正在刷新统计...')
        try:
            result = stats_service.evaluate_scores(
                term='2025-2026-2',
                class_name='2025级1班',
                operator_id='A001',
                trace_id='seed-demo',
            )
            print(f'[OK] 1班统计刷新完成: {result}')
        except Exception as e:
            print(f'[WARN] 1班统计刷新失败: {e}')
            db.session.rollback()

        try:
            result = stats_service.evaluate_scores(
                term='2025-2026-2',
                class_name='2025级2班',
                operator_id='A001',
                trace_id='seed-demo',
            )
            print(f'[OK] 2班统计刷新完成: {result}')
        except Exception as e:
            print(f'[WARN] 2班统计刷新失败: {e}')
            db.session.rollback()

        print('=' * 60)
        print('演示数据填充完成！')
        print('')
        print('账号说明:')
        print('  管理员: admin01 / 123456 (A001)')
        print('  教师1:  teacher01 / 123456 (T001, 张老师)')
        print('  教师2:  teacher02 / 123456 (T002, 李老师)')
        print('  学生:   student01~student20 / 123456 (S001~S020)')
        print('')
        print('课程说明:')
        print('  CHN01 语文 (3学分) | MATH01 数学 (4学分) | ENG01 英语 (3学分)')
        print('  PHY01 物理 (3学分) | CS01 计算机基础 (2学分)')
        print('')
        print('数据场景覆盖（2025级1班）:')
        print('  S001 赵一: 全科高分 (93/95/92/96/98) -> 总分474, 优秀')
        print('  S002 钱二: 全科中等 (74/75/72/70/78) -> 总分369, 中等')
        print('  S003 孙三: 偏科 (80/95/45/88/85) -> 偏科预警+低分预警')
        print('  S004 李四: 全科低分 (48/42/38/50/55) -> 总分233, 低分预警')
        print('  S005 周五: 与S001同分 -> 排名1,1,3验证')
        print('  S006 吴六: 数学59.99 -> 不及格边界')
        print('  S007 郑七: 数学60 -> 及格边界')
        print('  S008 王八: 数学89.99 -> 良好边界')
        print('  S009 冯九: 数学90 -> 优秀边界')
        print('  S010 陈十: 满分100 -> 全科满分')
        print('  S011 褚十一: 文科型 (92/55/90/48/75) -> 偏科预警')
        print('  S012 卫十二: 理科型 (58/96/52/94/90) -> 偏科预警')
        print('')
        print('数据场景覆盖（2025级2班）:')
        print('  S013 蒋十三: 优秀 | S014 沈十四: 良好 | S015 韩十五: 中等')
        print('  S016 杨十六: 及格线 | S017 朱十七: 偏科(物理98/英语40)')
        print('  S018 秦十八: 低分 | S019 尤十九: 边界综合 | S020 许二十: 中上')
        print('=' * 60)


if __name__ == '__main__':
    main()
