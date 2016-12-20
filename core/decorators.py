from functools import wraps
import time
import logging

import tornado.web


def measure(method_or_function):
    """Decorator that measures a method or function's time of execution.
    """
    @wraps(method_or_function)
    def decorator(*args, **kwargs):
        elapsed_time = time.time()
        result = method_or_function(*args, **kwargs)
        elapsed_time = (time.time() - elapsed_time) * 1000
        logging.info('{0}.{1}() executed in {2:.2f} milliseconds.'.format(
                method_or_function.__module__, method_or_function.__qualname__, elapsed_time))
        return result
    return decorator


def require_permissions(*required_permissions):
    """Decorator that checks if the user has required permissions.
    """
    def decorator(method):
        @wraps(method)
        def actual_decorator(handler, *args, **kwargs):
            # Check if the user is logged in.
            session = handler.get_session()
            if not session:
                return handler.on_login_required()
            # Check if the user has sufficient permissions.
            own_permissions = session['permissions']
            for required_permission in required_permissions:
                if required_permission not in own_permissions:
                    logging.warning('Insufficient permissions. ({0})'.format(handler.request.remote_ip))
                    raise tornado.web.HTTPError(403)
            return method(handler, *args, **kwargs)
        return actual_decorator
    return decorator

require_login = require_permissions()
