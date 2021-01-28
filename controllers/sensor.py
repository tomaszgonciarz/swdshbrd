from datetime import datetime, timezone, timedelta
from pytz import utc
import operator
import json
import humanfriendly
from models.entities_blubase2 import *
from models.entities_swdshbrd import *
from flask import render_template, jsonify, session, request, redirect, url_for
from sqlalchemy import func
from controllers.db_session import session_remote, session_heroku
from controllers.controllers import valid_ignores


def return_template(sensor_id):
    curr_ignores = valid_ignores(sensor_id=sensor_id)
    resp, ignore_incident = timeline(sensor_id)
    return render_template('sensor.html', resp=resp, ignore_incident=ignore_incident, sens_id=sensor_id, user_ign=curr_ignores['username'], time_ign=curr_ignores['ignore_untill'], name=session.get('username'), timeline_json=timeline_json(sensor_id))


def timeline_json(sensor_id):
    return json.dumps(timeline_data(sensor_id))


def return_json(sensor_id):
    json_data = {}
    json_data['data'] = []

    curr_date = datetime.now(timezone.utc)

    for idx, vpn_ip, mac, last_con, loc_name, account_name, phone, created_at, install_date in session_remote.query(Sensor.id, Sensor.vpn_ip, Sensor.eth, Sensor.last_heartbeat, Location.name, Account.name, Account.phone, Sensor.created_at, func.max(Installation.installed_at)).join(Installation, Sensor.id == Installation.sensor_id).join(Location, Location.id == Installation.location_id).join(Account, Sensor.account_id == Account.id).filter(Sensor.id == str(sensor_id), Installation.removed_at == None).group_by(Sensor.id).order_by(func.max(Installation.installed_at)):
        tmp = {}
        tmp['loc_name'] = loc_name
        tmp['account_name'] = account_name
        tmp['phone'] = phone
        tmp['vpn_ip'] = "<span onclick='copyToClipboard(this.innerHTML)' style='cursor:pointer;'>" + str(vpn_ip) + "</span>"
        tmp['sensor_id'] = idx
        tmp['eth'] = hex(int(mac))[2:]
        tmp['created_at'] = "<span class='time' data-unix_timestamp = '{}'".format(int(created_at.astimezone(utc).timestamp())) + '>' + str(created_at.astimezone(utc).timestamp()) + '</span>'

        if last_con is not None:
            tmp['last_heartbeat'] = "<span class='time' data-unix_timestamp = '{}'".format(int(last_con.astimezone(utc).timestamp())) + '>' + str(last_con.astimezone(utc).timestamp()) + '</span>'
        else:
            tmp['last_heartbeat'] = last_con

        json_data['data'].append(tmp)
    return jsonify(json_data)


def return_diagnostics_json(sensor_id):
    json_data = {}
    json_data['data'] = []

    data = session_remote.query(Diagnostic).filter(Diagnostic.sensor_id == sensor_id).all()

    for item in data:
        tmp = {}
        tmp['diagnostic_id'] = item.id
        tmp['restart_at'] = "<span class='time' data-unix_timestamp = '{}'".format(int(item.restart_at.astimezone(utc).timestamp())) + '>' + str(item.restart_at.astimezone(utc).timestamp()) + '</span>'
        tmp['free_space'] = item.free_space
        tmp['request_from_ip'] = item.request_from_ip
        tmp['timestamp'] = "<span class='time' data-unix_timestamp = '{}'".format(int(item.timestamp.astimezone(utc).timestamp())) + '>' + str(item.timestamp.astimezone(utc).timestamp()) + '</span>'
        tmp['free_memory'] = item.free_memory
        tmp['total_memory'] = item.total_memory
        tmp['total_space'] = item.total_space
        tmp['free_ramdisk'] = item.free_ramdisk
        tmp['total_ramdisk'] = item.total_ramdisk
        tmp['latency'] = str(item.latency)
        tmp['git_branch'] = item.git_branch
        tmp['git_commit'] = item.git_commit

        json_data['data'].append(tmp)
    return jsonify(json_data)


def return_heart_diagnostics_json(sensor_id):
    json_data = {}
    json_data['data'] = []

    data = session_remote.query(HeartbeatDiagnostic).filter(HeartbeatDiagnostic.sensor_id == sensor_id).all()

    for item in data:
        tmp = {}

        diagnostic_start = item.first_timestamp.astimezone(utc)
        diagnostic_end = item.last_timestamp.astimezone(utc)

        tmp['heartbeat_diagnostic_id'] = item.id
        tmp['heartbeat_count'] = item.heartbeat_count
        tmp['diagnositc_start'] = "<span class='time' data-unix_timestamp = '{}'".format(int(diagnostic_start.timestamp())) + '>' + str(diagnostic_start.timestamp()) + '</span>'
        tmp['diagnositc_end'] = "<span class='time' data-unix_timestamp = '{}'".format(int(diagnostic_end.timestamp())) + '>' + str(diagnostic_end.timestamp()) + '</span>'
        tmp['time_interval'] = humanfriendly.format_timespan(item.last_timestamp - item.first_timestamp)

        json_data['data'].append(tmp)
    return jsonify(json_data)


def return_data_graph_json(sensor_id):
    json_data = []

    data = session_remote.query(HeartbeatDiagnostic).filter(HeartbeatDiagnostic.sensor_id == sensor_id).all()

    for item in data:
        tmp = {}
        tmp['x'] = str(item.day)
        tmp['y'] = item.heartbeat_count
        json_data.append(tmp)
    return jsonify(json_data)


def timeline_data(sensor_id):
    data = []
    comments = session_heroku.query(Comment).filter(Comment.sensor_id == sensor_id).all()
    ignores = session_heroku.query(Ignore).filter(Ignore.sensor_id == sensor_id).all()
    incidents = session_heroku.query(Incident).filter(Incident.sensor_id == sensor_id).all()

    for item in comments:
        tmp = {}
        tmp['type'] = 'point'
        tmp['event_type'] = 'comment'
        tmp['start'] = item.created_at.isoformat()
        tmp['person'] = item.created_by
        tmp['value'] = item.comment
        tmp['content'] = "{}: {}".format(item.created_by, item.comment)
        data.append(tmp)

    for item in ignores:
        tmp = {}
        tmp['event_type'] = 'ignore'
        tmp['style'] = 'background-color: #6c757d;'
        tmp['start'] = item.created_at.isoformat()
        tmp['person'] = item.created_by
        tmp['value'] = item.reason
        tmp['untill'] = item.ignore_untill.isoformat()
        tmp['end'] = item.ignore_untill.isoformat()
        tmp['content'] = "ignore by {}: {}".format(item.created_by, item.reason)
        data.append(tmp)

    for item in incidents:
        tmp = {}
        tmp['event_type'] = 'incident'
        tmp['className'] = 'bg-danger'
        tmp['style'] = 'background-color: #dc3545;'
        tmp['start'] = item.start_at.isoformat()
        if not item.end_at == None:
            tmp['end_at'] = item.end_at.isoformat()
            tmp['end'] = item.end_at.isoformat()
        else:
            tmp['end_at'] = None
            tmp['end'] = datetime.now().isoformat()
        tmp['ignored'] = item.ignored
        data.append(tmp)

    data.sort(key=operator.itemgetter('start'), reverse=True)
    return data


def timeline(sensor_id):
    data = timeline_data(sensor_id)
    resp = []
    curr_incident = False
    ignored_str = '(ignored)'

    for item in data:
        if item['event_type'] == 'comment':
            resp.append("<li class='timeline-inverted'><div class='timeline-badge success'><i class='fa fa-graduation-cap'></i></div><div class='timeline-panel'><div class='timeline-heading'><h4 class='timeline-title'>Comment by {}</h4><p><small class='text-muted'><i class='fa fa-clock-o'></i>{}</small></p></div><div class='timeline-body'><p> {}</p></div></div></li>".format(item['person'], item['start'], item['value']))
        elif item['event_type'] == 'ignore':
            resp.append("<li class='timeline-inverted'><div class='timeline-badge info'><i class='fa fa-check'></i></div><div class='timeline-panel'><div class='timeline-heading'><h4 class='timeline-title'>Ignore by {0}, untill {1}</h4><p><small class='text-muted'><i class='fa fa-clock-o'></i>{2}</small></p></div><div class='timeline-body'><p> {3}</p><hr><div class='btn-group'><button type='button' class='btn btn-primary btn-sm dropdown-toggle' data-toggle='dropdown'><i class='fa fa-gear'></i> <span class='caret'></span></button><ul class='dropdown-menu' role='menu'><li><a href='{5}'>Delete ignore</a></li></ul></div></div></div></li>".format(item['person'], item['untill'], item['start'], item['value'], sensor_id, url_for('delete_ignore', sensor_id=sensor_id)))
        else:
            if item['end_at']:
                resp.append("<li><div class='timeline-badge'><i class='fa fa-bomb'></i></div><div class='timeline-panel'><div class='timeline-heading'><h4 class='timeline-title'>Incident</h4></div><div class='timeline-body'><p>Start at: {}, end at: {}</p></div></div></li>".format(item['start'], item['end_at']))
            else:
                if not item['ignored']:
                    curr_incident = True
                    ignored_str = ''
                resp.append("<li><div class='timeline-badge danger'><i class='fa fa-bomb'></i></div><div class='timeline-panel'><div class='timeline-heading'><h4 class='timeline-title'>Incident {}</h4></div><div class='timeline-body'><p>Start at: {}, still in progress</p><hr><div class='btn-group'><button type='button' class='btn btn-primary btn-sm dropdown-toggle' data-toggle='dropdown'><i class='fa fa-gear'></i> <span class='caret'></span></button><ul class='dropdown-menu' role='menu'><li><a href='{}'>Ignore incident</a></li><li><a href='{}'>Delete ignore</a></li></ul></div></div></div></li>".format(ignored_str, item['start'], url_for('ignore_incident', sensor_id=sensor_id), url_for('delete_ignore_on_incident', sensor_id=sensor_id)))
    return resp, curr_incident


def add_comment(sensor_id):
    if request.method == 'GET':
        return render_template('comment.html', sens_id=sensor_id, name=session.get('username'))
    elif request.method == 'POST':
        if request.form.get('usrname') == '' or request.form.get('comment') == '':
            flash('Invalid username or comment')
            return render_template('comment.html', sens_id=sensor_id, name=session.get('username'))
        else:
            new = Comment(
                sensor_id=sensor_id,
                created_at=datetime.now(timezone.utc),
                comment=request.form.get('comment'),
                created_by=request.form.get('usrname')
            )
            session_heroku.add(new)
            session_heroku.commit()
            return redirect(url_for('sensor_info', sensor_id=sensor_id))


def add_ignore(sensor_id):
    default_date = (datetime.now(timezone.utc) + timedelta(days=14)).strftime("%Y-%m-%dT%H:%M")
    if request.method == 'GET':
        return render_template('ignore.html', sens_id=sensor_id, date=default_date, name=session.get('username'))
    elif request.method == 'POST':
        if request.form.get('reason') == '' or request.form.get('datetime') == '':
            flash('Invalid reason or date')
            return render_template('ignore.html', sens_id=sensor_id, date=default_date, name=session.get('username'))
        else:
            new = Ignore(
                sensor_id=sensor_id,
                created_at=datetime.now(timezone.utc),
                reason=request.form.get('reason'),
                ignore_untill=datetime.strptime(request.form.get('datetime'), '%Y-%m-%dT%H:%M').astimezone(utc),
                created_by=request.form.get('usrname')
            )
            return_delete_ignore(sensor_id)
            session_heroku.add(new)
            session_heroku.commit()
            return redirect(url_for('sensor_info', sensor_id=sensor_id))

def ignore_incident(sens_id):
    incident = session_heroku.query(Incident).filter(Incident.sensor_id == sens_id, Incident.end_at == None).first()
    incident.ignored = True
    session_heroku.commit()
    return redirect(url_for('sensor_info', sensor_id=sens_id))

def delete_ignore_on_incident(sens_id):
    incident = session_heroku.query(Incident).filter(Incident.sensor_id == sens_id, Incident.end_at == None).first()
    incident.ignored = False
    session_heroku.commit()
    return redirect(url_for('sensor_info', sensor_id=sens_id))

def return_delete_ignore(sensor_id):
    old = session_heroku.query(Ignore).filter(Ignore.sensor_id == sensor_id).first()
    if old:
        session_heroku.delete(old)
    return redirect(url_for('sensor_info', sensor_id=sensor_id))
