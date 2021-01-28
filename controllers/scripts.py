from datetime import datetime, timezone, timedelta
from pytz import utc
from models.entities_blubase2 import *
from models.entities_swdshbrd import *
from controllers.db_session import session_heroku, session_remote, engine_heroku, engine_remote
import click


def new_incidents():
    curr_date = datetime.now(timezone.utc)
    last_active_at = curr_date - timedelta(minutes=30)

    results = engine_remote.execute('SELECT sensors.id, sensors.last_heartbeat, MIN(inactivity_alerts.interval) FROM sensors JOIN installations ON installations.sensor_id = sensors.id JOIN locations ON locations.id = installations.location_id JOIN inactivity_alerts ON locations.id = inactivity_alerts.location_id WHERE last_heartbeat IS NOT NULL AND last_heartbeat < "{}" AND installations.removed_at IS NULL GROUP BY inactivity_alerts.location_id'.format(last_active_at))
    for row in results:
        sensor_id = row[0]
        timestamp = row[1]
        inactivity_interval = row[2]
        click.echo("Incident on " + str(sensor_id) + ", last active at: " + str(timestamp))

        incident_is_new = (engine_heroku.execute('SELECT COUNT(*) FROM incidents WHERE sensor_id = {} AND start_at = \'{}\''.format(sensor_id, timestamp)).scalar() == 0)

        if incident_is_new:
            if inactivity_interval == None:
                alert_at = None
            else:
                alert_at = (timestamp + timedelta(seconds=inactivity_interval))

            click.echo("NEW Incident on " + str(sensor_id) + ", last active at: " + str(timestamp))

            new_incident = Incident(
                sensor_id=sensor_id,
                start_at=timestamp.astimezone(utc),
                created_at=curr_date.astimezone(utc),
                alert_at=alert_at.astimezone(utc),
                end_at=None
            )
            session_heroku.add(new_incident)
    session_heroku.commit()


def resolved_incidents():
    incidents = {}
    sensor_ids = []
    data = session_heroku.query(Incident).filter(Incident.end_at == None).all()
    for item in data:
        incidents[item.sensor_id] = item.start_at
        sensor_ids.append(str(item.sensor_id))

    sensor_ids = ','.join(sensor_ids)

    sensors = engine_remote.execute('SELECT id, last_heartbeat FROM sensors WHERE last_heartbeat IS NOT NULL AND id in ({})'.format(sensor_ids))
    for sensor in sensors:
        sensor_id, last_heartbeat = sensor
        if incidents[sensor_id].replace(tzinfo=utc) < last_heartbeat.replace(tzinfo=utc):
            click.echo("Incident on " + str(sensor_id) + ", last active at: " + str(last_heartbeat))
            curr_incident = session_heroku.query(Incident).filter(Incident.sensor_id == sensor_id, Incident.end_at == None).first()
            curr_incident.end_at = last_heartbeat.astimezone(utc)
    session_heroku.commit()


def old_incidents():
    curr_date = datetime.now(timezone.utc)
    old_incidents = session_heroku.query(Incident).filter(Incident.created_at < (curr_date - timedelta(days=14))).delete()
    session_heroku.commit()
