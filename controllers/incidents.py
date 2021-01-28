from datetime import datetime, timezone, timedelta
from pytz import utc
import humanfriendly
from models.entities_blubase2 import *
from models.entities_swdshbrd import *
from flask import url_for, render_template, jsonify, request, session
from controllers.db_session import session_remote, engine_heroku, session_heroku
from controllers.controllers import valid_ignores, check_int
from sqlalchemy import or_, func


CURR_DATE = datetime.now(timezone.utc)


def return_template():
    return render_template('index.html', name=session.get('username'))


def return_json():
    json_data = {}
    params = {}
    sensor_ids = ()
    json_data['data'] = []
    incident_info = {}
    sensor_info = {}

    datatables_request = request.form
    for item in datatables_request.items():
        params[item[0]] = item[1]

    order_column = params['order[0][column]']
    order_direction = params['order[0][dir]']
    order = {'0': 'sensor_id', '4': 'start_at', '5': 'duration', '6': 'end_at'}

    search_value = params['search[value]']
    offset = abs(int(params['start']))
    limit = abs(int(params['length']))

    if params['ignores'] == 'true':
        show_ignores = True
    else:
        show_ignores = False

    if params['inactivity'] == 'true':
        show_within_threshold = True
    else:
        show_within_threshold = False

    if params['finished_incidents'] == 'true':
        show_finished_incidents = True
    else:
        show_finished_incidents = False

    if search_value == '':
        incidents_query_str = create_query_str(show_ignores, show_within_threshold, show_finished_incidents, order[order_column], order_direction, search_value, search_int=False, search_str=False, sensor_ids=None)

        incident_info, sensor_ids, records_filtered = create_incident_info(incidents_query_str, limit, offset)

        sensors = session_remote.query(Sensor.id, Sensor.last_heartbeat, Location.name, Account.id, func.min(InactivityAlert.interval)).join(Installation, Sensor.id == Installation.sensor_id).join(Location, Location.id == Installation.location_id).join(Account, Sensor.account_id == Account.id).join(InactivityAlert, InactivityAlert.location_id == Location.id).filter(Sensor.id.in_(sensor_ids), Installation.removed_at == None).group_by(InactivityAlert.location_id).all()

        sensor_info, none = create_sensor_info(sensors)

    elif check_int(search_value):
        incidents_query_str = create_query_str(show_ignores, show_within_threshold, show_finished_incidents, order[order_column], order_direction, search_value, search_int=True, search_str=False, sensor_ids=None)

        incident_info, sensor_ids, records_filtered = create_incident_info(incidents_query_str, limit, offset)

        sensors = session_remote.query(Sensor.id, Sensor.last_heartbeat, Location.name, Account.id, func.min(InactivityAlert.interval)).join(Installation, Sensor.id == Installation.sensor_id).join(Location, Location.id == Installation.location_id).join(Account, Sensor.account_id == Account.id).join(InactivityAlert, InactivityAlert.location_id == Location.id).filter(Sensor.id.in_(sensor_ids), Installation.removed_at == None).group_by(InactivityAlert.location_id).all()

        sensor_info, none = create_sensor_info(sensors)

    else:
        sensors = session_remote.query(Sensor.id, Sensor.last_heartbeat, Location.name, Account.id, func.min(InactivityAlert.interval)).join(Installation, Sensor.id == Installation.sensor_id).join(Location, Location.id == Installation.location_id).join(Account, Sensor.account_id == Account.id).join(InactivityAlert, InactivityAlert.location_id == Location.id).filter(Location.name.like('%' + search_value + '%'), Installation.removed_at == None).group_by(InactivityAlert.location_id).all()

        sensor_info, sensor_ids = create_sensor_info(sensors)

        incidents_query_str = create_query_str(show_ignores, show_within_threshold, show_finished_incidents, order[order_column], order_direction, search_value, search_int=False, search_str=True, sensor_ids=sensor_ids)

        incident_info, sensor_ids, records_filtered = create_incident_info(incidents_query_str, limit, offset)

    json_data = create_json_data(incident_info, sensor_info, sensor_ids)
    json_data['recordsTotal'] = session_heroku.query(func.count(Incident.id)).scalar()
    json_data['recordsFiltered'] = records_filtered

    return jsonify(json_data)


def create_incident_info(incidents_query_str, limit, offset):
    sensor_ids = ()
    records_filtered = 0

    incidents = engine_heroku.execute(incidents_query_str)
    for incident in incidents:
        records_filtered += 1

    incidents = engine_heroku.execute(incidents_query_str + " LIMIT {} OFFSET {}".format(limit, offset))
    incidents = [i for i in incidents]

    for incident in incidents:
        sensor_ids += (incident[0],)

    return incidents, sensor_ids, records_filtered


def create_sensor_info(sensors):
    sensor_info = {}
    sensor_ids = []

    for sensor in sensors:
        tmp = []
        sensor_ids.append(str(sensor[0]))
        if sensor[1] is not None:
            tmp.append(sensor[1].astimezone(utc))
            tmp.append(sensor[3])
            tmp.append(sensor[2])
        else:
            tmp.append('')
            tmp.append('')
            tmp.append('')
        sensor_info[sensor[0]] = tmp
    sensor_ids = '(' + ','.join(sensor_ids) + ')'
    return sensor_info, sensor_ids


def create_json_data(incident_info, sensor_info, sensor_ids):
    json_data = {}
    json_data['data'] = []
    curr_ignores = valid_ignores()

    ids_comment_after, ids_comment_before = get_sensor_id_commented_incidents()

    for incident in incident_info:
        tmp = {}

        sensor_id = incident[0]
        status = ''
        if incident[0] in curr_ignores or incident[6]:
            status = 'Ignored'
        elif incident[4].astimezone(utc) >= CURR_DATE:
            status = 'Within threshold'
        else:
            status = 'Error'

        sensor_id_cell_str = "<a href = {}>{}</a> <span class='label label-primary'>{}</span>".format(url_for('sensor_info', sensor_id=sensor_id), sensor_id, status)

        if incident[5] in ids_comment_after:
            sensor_id_cell_str += " <span class='label label-success'; display:block;><i class='fa fa-user fa-fw'></i></span>"

        if incident[5] in ids_comment_before:
            sensor_id_cell_str += " <span class='label label-default'; display:block;><i class='fa fa-comment fa-fw'></i></span>"

        tmp['sensor_id'] = sensor_id_cell_str
        tmp['start_at'] = "<span class='time timeago' data-unix_timestamp = '{}'".format(int(incident[1].astimezone(utc).timestamp())) + '>' + str(incident[1].astimezone(utc).timestamp()) + '</span>'
        tmp['duration'] = humanfriendly.format_timespan(incident[3])
        if incident[2] is not None:
            tmp['end_at'] = "<span class='time timeago' data-unix_timestamp = '{}'".format(int(incident[2].astimezone(utc).timestamp())) + '>' + str(incident[2].astimezone(utc).timestamp()) + '</span>'
        else:
            tmp['end_at'] = incident[2]

        if sensor_id in sensor_info.keys():
            tmp['last_heartbeat'] = "<span class='time' data-unix_timestamp = '{}'".format(int(sensor_info[sensor_id][0].astimezone(utc).timestamp())) + '>' + str(sensor_info[sensor_id][0].astimezone(utc).timestamp()) + '</span>'
            tmp['account_id'] = sensor_info[sensor_id][1]
            tmp['location_name'] = sensor_info[sensor_id][2]
        else:
            tmp['last_heartbeat'] = 'Not installed'
            tmp['account_id'] = 'Not installed'
            tmp['location_name'] = 'Not installed'
        json_data['data'].append(tmp)
    return json_data


def create_query_str(show_ignores, show_within_threshold, show_finished_incidents, order_column, order_direction, search_value, search_int, search_str, sensor_ids=None):
    condition = ''
    condition_query_str = ''
    incidents_query_str = "SELECT incidents.sensor_id, start_at, end_at, CASE WHEN end_at IS NULL THEN extract(EPOCH FROM(now() - start_at)) ELSE extract(EPOCH FROM(end_at - start_at)) END AS duration, alert_at, incidents.id, incidents.ignored FROM incidents LEFT JOIN ignores ON incidents.sensor_id = ignores.sensor_id"

    num_of_conditions = 0

    # add WHERE to query
    if not show_ignores:
        condition = " incidents.ignored = false AND (ignores.sensor_id IS NULL OR ignores.ignore_untill < '{}')".format(CURR_DATE)
        condition_query_str, num_of_conditions = add_query_str(condition, num_of_conditions)
        incidents_query_str += condition_query_str

    if not show_within_threshold:
        condition = " alert_at < '{}'".format(CURR_DATE)
        condition_query_str, num_of_conditions = add_query_str(condition, num_of_conditions)
        incidents_query_str += condition_query_str

    if not show_finished_incidents:
        condition = " end_at IS NULL"
        condition_query_str, num_of_conditions = add_query_str(condition, num_of_conditions)
        incidents_query_str += condition_query_str

    if search_int:
        condition = " CAST(incidents.sensor_id AS VARCHAR) LIKE '%%{}%%'".format(search_value)
        condition_query_str, num_of_conditions = add_query_str(condition, num_of_conditions)
        incidents_query_str += condition_query_str

    if search_str and len(sensor_ids) > 2:
        condition = " incidents.sensor_id IN {}".format(sensor_ids)
        condition_query_str, num_of_conditions = add_query_str(condition, num_of_conditions)
        incidents_query_str += condition_query_str
    elif search_str and len(sensor_ids) == 2:
        condition = " incidents.sensor_id IS NULL"
        condition_query_str, num_of_conditions = add_query_str(condition, num_of_conditions)
        incidents_query_str += condition_query_str

    incidents_query_str += " ORDER BY {} {}".format(order_column, order_direction)

    return incidents_query_str


def add_query_str(new_query_str, num_of_conditions):
    query_str = ''
    if num_of_conditions == 0:
        query_str += ' WHERE'
        num_of_conditions += 1
    else:
        query_str += ' AND'
    query_str += new_query_str
    return query_str, num_of_conditions


def get_sensor_id_commented_incidents():
    sensor_ids_after = ()
    sensor_ids_before = ()

    sensors_comment_after_incident = engine_heroku.execute("SELECT incidents.id, MAX(incidents.created_at), incidents.sensor_id FROM incidents JOIN comments ON comments.sensor_id = incidents.sensor_id WHERE incidents.created_at < comments.created_at GROUP BY incidents.sensor_id, incidents.id")
    for sensor in sensors_comment_after_incident:
        sensor_ids_after += (sensor[0],)

    sensors_comment_before_incident = engine_heroku.execute("SELECT incidents.id, MAX(incidents.created_at), incidents.sensor_id FROM incidents JOIN comments ON comments.sensor_id = incidents.sensor_id WHERE incidents.created_at > comments.created_at GROUP BY incidents.sensor_id, incidents.id")
    for sensor in sensors_comment_before_incident:
        sensor_ids_before += (sensor[0],)

    return sensor_ids_after, sensor_ids_before
