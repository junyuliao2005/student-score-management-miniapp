"""密码哈希工具"""
from werkzeug.security import generate_password_hash, check_password_hash


def hash_password(password):
    """生成密码哈希"""
    return generate_password_hash(password, method='pbkdf2:sha256')


def verify_password(password, password_hash):
    """校验密码"""
    return check_password_hash(password_hash, password)
