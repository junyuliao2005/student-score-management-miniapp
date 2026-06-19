import logging
from flask import Flask
from config import Config
from app.extensions import db, cors

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)


def create_app(config_class=None):
    app = Flask(__name__)

    if config_class is None:
        app.config.from_object(Config)
    else:
        app.config.from_object(config_class)

    # 初始化扩展
    db.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": "*"}})

    # 注册模型（确保表被 SQLAlchemy 识别）
    from app.models import user, role, course, score, sys_config, audit_log
    from app.models import ai_analysis, exam_paper, message, exam_publish

    # 注册中间件
    from app.middleware.trace_middleware import init_trace_middleware
    init_trace_middleware(app)

    from app.middleware.error_handlers import register_error_handlers
    register_error_handlers(app)

    # 注册蓝图
    from app.routes import register_blueprints
    register_blueprints(app)

    # 健康检查接口
    @app.route('/', methods=['GET'])
    def root_health():
        return {'status': 'ok', 'service': 'student-grade-backend'}

    @app.route('/api/health', methods=['GET'])
    def health():
        from app.utils.response import success
        return success({'status': 'ok', 'version': '1.0.0'})

    return app
