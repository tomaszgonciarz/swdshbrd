from datetime import datetime, timezone, timedelta
from pytz import utc
from models.entities_blubase2 import *
from flask import url_for, render_template, jsonify, session
from sqlalchemy import func
from controllers.db_session import session_remote
from controllers.controllers import valid_ignores


def return_template():
    return render_template('sensors_list.html', name=session.get('username'))


def return_json():
    json_data = {}
    json_data['data'] = []
    curr_date = datetime.now(timezone.utc)

    current_ignores = valid_ignores()

    for idx, vpn_ip, mac, last_con, loc_name, account_name, phone, install_date in session_remote.query(Sensor.id, Sensor.vpn_ip, Sensor.eth, Sensor.last_heartbeat, Location.name, Account.name, Account.phone, func.max(Installation.installed_at)).join(Installation, Sensor.id == Installation.sensor_id).join(Location, Location.id == Installation.location_id).join(Account, Sensor.account_id == Account.id).filter(Installation.removed_at == None).group_by(Sensor.id).order_by(func.max(Installation.installed_at)):

        tmp = {}
        tmp['loc_name'] = loc_name
        tmp['vpn_ip'] = "<span onclick='copyToClipboard(this.innerHTML)' style='cursor:pointer;'>" + str(vpn_ip) + "</span>"
        tmp['account_name'] = account_name
        tmp['phone'] = phone
        tmp['sensor_id'] = "<a href = {}>{}</a>".format(url_for('sensor_info', sensor_id=idx), idx)
        tmp['eth'] = hex(int(mac))[2:]

        if last_con is not None:
            last_date = last_con.astimezone(utc)
            time_difference = (curr_date - last_date) / timedelta(hours=1)
            tmp['last_heartbeat_time'] = round(time_difference)
            tmp['last_heartbeat'] = "<span class='time' data-unix_timestamp = '{}'".format(int(last_con.astimezone(utc).timestamp())) + '>' + str(last_con.astimezone(utc).timestamp()) + '</span>'
        else:
            tmp['last_heartbeat_time'] = last_con
            tmp['last_heartbeat'] = last_con

        tmp['ignore'] = (idx in current_ignores)

        json_data['data'].append(tmp)
    return jsonify(json_data)
