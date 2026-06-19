from datetime import datetime
from app.extensions import db

_id_type = db.BigInteger().with_variant(db.Integer, "sqlite")


class SysConfig(db.Model):
    __tablename__ = 'sys_config'

    config_id = db.Column(_id_type, primary_key=True, autoincrement=True)
    config_key = db.Column(db.String(64), unique=True, nullable=False)
    config_value = db.Column(db.String(255), nullable=False)
    config_type = db.Column(db.String(20), nullable=False, comment='int/string/json/bool')
    scope = db.Column(db.String(20), nullable=False, default='global')
    remark = db.Column(db.String(255), nullable=True)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            'config_id': self.config_id,
            'config_key': self.config_key,
            'config_value': self.config_value,
            'config_type': self.config_type,
            'scope': self.scope,
            'remark': self.remark,
        }
