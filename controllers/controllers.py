from datetime import datetime, timezone, timedelta
from controllers.db_session import session_heroku
from models.entities_swdshbrd import *
from sqlalchemy import func
from pytz import utc
from flask import session, request, url_for, redirect
from functools import wraps


def valid_ignores(sensor_id=None):
    curr_date = datetime.now(timezone.utc)
    if sensor_id is None:
        valid_ignores = []

        for idx, ignore_untill in session_heroku.query(Ignore.sensor_id, func.max(Ignore.ignore_untill)).group_by(Ignore.sensor_id).all():
            if ((ignore_untill.astimezone(utc) - curr_date) / timedelta(minutes=1)) > 0:
                valid_ignores.append(idx)
    else:
        valid_ignores = {}
        valid_ignores['username'] = None
        valid_ignores['ignore_untill'] = None

        for idx, username, ignore_untill in session_heroku.query(Ignore.sensor_id, Ignore.created_by, func.max(Ignore.ignore_untill)).filter(Ignore.sensor_id == sensor_id).group_by(Ignore.sensor_id, Ignore.created_by).all():
            if ((ignore_untill.astimezone(utc) - curr_date) / timedelta(minutes=1)) > 0:
                valid_ignores['username'] = username
                valid_ignores['ignore_untill'] = ignore_untill.astimezone(utc).isoformat()
    return valid_ignores


def check_int(s):
    if s[0] in ('-', '+'):
        return s[1:].isdigit()
    return s.isdigit()


def username():
    if request.form.get('username'):
        session['username'] = request.form.get('username')
    return redirect(url_for('dashboard', name=session.get('username')))
