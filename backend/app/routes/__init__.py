"""蓝图注册"""


def register_blueprints(app):
    from app.routes.auth_routes import auth_bp
    from app.routes.config_routes import config_bp
    from app.routes.admin_routes import admin_bp
    from app.routes.score_routes import score_bp
    from app.routes.score_import_routes import score_import_bp
    from app.routes.user_import_routes import user_import_bp
    from app.routes.stats_routes import stats_bp
    from app.routes.warning_routes import warning_bp
    from app.routes.message_routes import message_bp
    from app.routes.options_routes import options_bp
    from app.routes.exam_publish_routes import exam_publish_bp
    from app.routes.upload_routes import upload_bp
    from app.routes.teacher_binding_routes import teacher_binding_bp
    from app.routes.import_batch_routes import import_batch_bp
    from app.routes.analytics_routes import analytics_bp
    from app.routes.report_routes import report_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(config_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(score_bp)
    app.register_blueprint(score_import_bp)
    app.register_blueprint(user_import_bp)
    app.register_blueprint(stats_bp)
    app.register_blueprint(warning_bp)
    app.register_blueprint(message_bp)
    app.register_blueprint(options_bp)
    app.register_blueprint(exam_publish_bp)
    app.register_blueprint(upload_bp)
    app.register_blueprint(teacher_binding_bp)
    app.register_blueprint(import_batch_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(report_bp)

    from app.routes.ai_routes import ai_bp
    app.register_blueprint(ai_bp)
