"""
himat 身份验证模块
提供 Bearer Token 验证功能，通过 JWT 解密获取 user_id
"""

from functools import wraps
from flask import request, jsonify, g
import jwt

from .config import Config
from .utils.logger import get_logger

logger = get_logger('mirofish.auth')


def verify_himat_token():
    """
    从请求头中验证 himat Bearer Token。

    通过 JWT HS256 解密 Token，从 payload 中提取 user_id。

    Returns:
        str: 验证通过的 user_id，失败返回 None
    """
    auth_header = request.headers.get('Authorization', '')

    if not auth_header or not auth_header.startswith('Bearer '):
        return None

    token = auth_header[len('Bearer '):]
    if not token:
        return None

    try:
        payload = jwt.decode(token, Config.JWT_SECRET, algorithms=["HS256"])
        user_id = payload.get('sub')
        if not user_id:
            logger.warning(f"JWT payload 中缺少 sub 字段: {list(payload.keys())}")
            return None
        logger.debug(f"himat Token 验证通过: user_id={user_id}, username={payload.get('username')}")
        return user_id
    except jwt.ExpiredSignatureError:
        logger.warning("himat Token 已过期")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"himat Token 无效: {e}")
        return None


def require_auth(f):
    """
    路由装饰器：要求请求必须携带有效的 himat Token。
    验证通过后将 user_id 存入 flask.g.user_id。
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = verify_himat_token()
        if not user_id:
            return jsonify({
                "success": False,
                "error": "未授权：请提供有效的 himat Token（Authorization: Bearer <token>）"
            }), 401
        g.user_id = user_id
        return f(*args, **kwargs)
    return decorated_function


def get_current_user_id() -> str:
    """
    获取当前请求的 user_id。
    如果未通过鉴权中间件，尝试从 Token 解析；若无 Token 则返回 'anonymous'。
    """
    # 优先从 g 中获取（已通过 require_auth 装饰器）
    user_id = getattr(g, 'user_id', None)
    if user_id:
        return user_id

    # 尝试从 Token 解析
    user_id = verify_himat_token()
    if user_id:
        return user_id

    return 'anonymous'
