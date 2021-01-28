import jinja2.exceptions
from datetime import timedelta
from flask import Flask, send_from_directory, session, request, Response, redirect
from controllers import incidents, sensors, sensor, scripts, controllers
from flask_sslify import SSLify

app = Flask(__name__)
app.secret_key = bytes.fromhex(
    'dfba670ebc21410076bb5941140e789ac6342e09c18da920'
)

@app.route('/')
@app.route('/index')
def dashboard():
    return incidents.return_template()


@app.route('/dashboard', methods=['POST'])
def dashboard_json():
    return incidents.return_json()


@app.route('/sensors')
def sensors_list():
    return sensors.return_template()


@app.route('/sensors_json')
def sensors_json():
    return sensors.return_json()


@app.route('/sensors/<int:sensor_id>')
def sensor_info(sensor_id):
    return sensor.return_template(sensor_id)


@app.route('/sensor/<int:sensor_id>')
def sensor_info_json(sensor_id):
    return sensor.return_json(sensor_id)


@app.route('/diagnostics/<int:sensor_id>')
def diagnostics(sensor_id):
    return sensor.return_diagnostics_json(sensor_id)


@app.route('/heartdiagnostics/<int:sensor_id>')
def heart_diagnostics(sensor_id):
    return sensor.return_heart_diagnostics_json(sensor_id)


@app.route('/data_graph/<int:sensor_id>')
def data_graph(sensor_id):
    return sensor.return_data_graph_json(sensor_id)


@app.route('/default_username', methods=['POST'])
def set_username():
    return controllers.username()


@app.route('/delete_ignore/<int:sensor_id>')
def delete_ignore(sensor_id):
    return sensor.return_delete_ignore(sensor_id)


@app.route('/ignore_incident/<int:sensor_id>')
def ignore_incident(sensor_id):
    return sensor.ignore_incident(sensor_id)


@app.route('/delete_ignore_on_incident/<int:sensor_id>')
def delete_ignore_on_incident(sensor_id):
    return sensor.delete_ignore_on_incident(sensor_id)


@app.route('/sensors/comment/<int:sensor_id>', methods=['GET', 'POST'])
def comment_form(sensor_id):
    return sensor.add_comment(sensor_id)


@app.route('/sensors/ignore/<int:sensor_id>', methods=['GET', 'POST'])
def ignore_form(sensor_id):
    return sensor.add_ignore(sensor_id)


@app.route('/<path:resource>')
def serveStaticResource(resource):
    return send_from_directory('static/', resource)


@app.errorhandler(jinja2.exceptions.TemplateNotFound)
def template_not_found(e):
    return not_found(e)


@app.errorhandler(404)
def not_found(e):
    return '<strong>Page Not Found!</strong>', 404


@app.cli.command()
def find_new_incidents():
    return scripts.new_incidents()


@app.cli.command()
def find_resolved_incidents():
    return scripts.resolved_incidents()

@app.cli.command()
def delete_old_incidents():
    return scripts.old_incidents()

@app.before_request
def requires_basic_auth():
    sslify = SSLify(app)

    if 'logged' not in session.keys():
        auth = request.authorization
        if not auth or not check_auth(auth.password):
            return please_authenticate()
        elif 'username' not in session.keys():
            session.permanent = True
            app.permanent_session_lifetime = timedelta(days=7)
            session['username'] = auth.username
            session['logged'] = True


def please_authenticate():
    """Sends a 401 response that enables basic auth"""
    return Response('Could not verify your access level for that URL.\n'
                    'You have to login with proper credentials', 401,
                    {'WWW-Authenticate': 'Basic realm="Login Required"'})


def check_auth(password):
    """This function is called to check if a username password combination is
    valid."""
    return password == 'SuperSecretPassword'

if __name__ == '__main__':
    app.debug = False
    app.run(ssl_context='adhoc')
