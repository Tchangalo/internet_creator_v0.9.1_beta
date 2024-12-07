import eventlet
eventlet.monkey_patch()
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_socketio import SocketIO, emit
import subprocess
import os
import select
import threading
import time
import re

app = Flask(__name__)
app.secret_key = 'my_secret_key'  # Hier einen sicheren Schlüssel verwenden
#socketio = SocketIO(app)
socketio = SocketIO(app, async_mode='eventlet', logger=False, engineio_logger=False, ping_timeout=20, ping_interval=10)

GENERAL_SCRIPT_DIR = "/home/user/streams/ks/"
SCRIPT_DIR = "/home/user/streams/"
IMAGE_PATH = "/static/style/mplan.svg"

def ensure_config_dir_exists():
    if not os.path.exists(GENERAL_SCRIPT_DIR):
        os.makedirs(GENERAL_SCRIPT_DIR)

def call_script(script_dir, script_name, process_type=None, *args):
    command = f"bash {script_dir}{script_name} {' '.join(map(str, args))}"
    print(f"Executing command: {command}")  # Debug-Ausgabe

    env = os.environ.copy()
    env["ANSIBLE_FORCE_COLOR"] = "true"

    # Liste von Keywords, die in den zu ignorierenden Warnungen vorkommen
    ignore_keywords = ["interpreter", "ansible", "python", "idempotency", "configuration", "device"]

    try:
        with subprocess.Popen(command, shell=True, executable="/bin/bash",
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              text=True, env=env, bufsize=1) as process:
            while True:
                reads = [process.stdout.fileno(), process.stderr.fileno()]
                ret = select.select(reads, [], [])
                # Echtzeitausgabe von stdout (Download-Status)
                if process.stdout.fileno() in ret[0]:
                    line = process.stdout.readline()
                    if line:
                        print(line, end='', flush=True)  # Echtzeitausgabe für stdout
                # Filtern und Ausblenden von Warnungen basierend auf Keywords
                if process.stderr.fileno() in ret[0]:
                    line = process.stderr.readline()
                    if line:
                        # Ignorieren, wenn eine der Ignore-Keywords in der Zeile vorkommt
                        if not any(keyword in line.lower() for keyword in ignore_keywords):
                            print(line, end='', flush=True)  # Andere Fehler sofort anzeigen
                # Beenden, wenn der Prozess abgeschlossen ist
                if process.poll() is not None:
                    break
            # Warten, bis der Prozess vollständig abgeschlossen ist
            process.wait()

            if process.returncode == 0:
                if process_type == "toggle_mode":
                    pass
                else:
                    flash(f"Script {script_name} executed successfully!", "success")
            else:
                flash(f"Script {script_name} failed with exit code {process.returncode}.", "error")

    except FileNotFoundError:
        flash(f"Script {script_name} not found or invalid command!", "error")
        print(f"Script {script_name} not found or invalid command!")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/toggle_mode', methods=['POST'])
def toggle_mode():
    mode = request.json.get("mode")
    call_script(SCRIPT_DIR, "togglemode.sh", "toggle_mode", mode)
    return '', 204

@app.route('/setup', methods=['GET', 'POST'])
def setup():
    if request.method == 'POST':
        errors = []
        if 'create_vyos_qcow2' in request.form:
            vm_username = request.form.get("VM Username", "").strip()
            vm_ip = request.form.get("VM IP", "").strip()
            pve_ip = request.form.get("PVE IP", "").strip()
            version_no = request.form.get("Version No", "").strip()

            ipv4_regex = r"^(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\." \
                         r"(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\." \
                         r"(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\." \
                         r"(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
            
            if not vm_username or not vm_ip or not pve_ip or not version_no:
                errors.append("At least one field was left empty!")
            elif not re.match(ipv4_regex, vm_ip):
                errors.append("Invalid VM IP address!")
            elif not re.match(ipv4_regex, pve_ip):
                errors.append("Invalid PVE IP address!")
            elif vm_ip == pve_ip:
                errors.append("VM IP cannot equal PVE IP!")
            
            if errors:
                for error in errors:
                    flash(error, "error")
                return redirect(url_for('setup'))

            args = [vm_username, vm_ip, pve_ip, version_no]
            call_script(SCRIPT_DIR, 'startvyosqcow2.sh', "create_vyos_qcow2", *args)

        elif 'create_seed' in request.form:
            call_script(SCRIPT_DIR, 'seed.sh', "create_seed")

        return redirect(url_for('setup'))
    return render_template('setup.html')

@app.route('/creator', methods=['GET', 'POST'])
def creator():
    if request.method == 'POST':
        errors = []
        provider = request.form.get("Provider", "").strip()
        first_router = request.form.get("First Router", "").strip()
        last_router = request.form.get("Last Router", "").strip()
        start_delay = request.form.get("Start Delay", "").strip()

        if not provider or not first_router or not last_router or 'provider' in request.form and not start_delay:
            errors.append("At least one field was left empty!")
        elif not provider.isdigit() or not first_router.isdigit() or not last_router.isdigit() or 'provider' in request.form and not start_delay.isdigit():
            errors.append("At least one field was not filled with a digit!")
        elif int(provider) > 3:
            errors.append("The provider cannot be higher than 3!")
        elif int(first_router) > 9 or int(last_router) > 9:
            errors.append("The number of routers cannot be greater than 9!")
        elif int(first_router) > int(last_router):
            errors.append("The number of 'Last Router' cannot be smaller than the number of 'First Router'!")

        if errors:
            for error in errors:
                flash(error, "error")
            return redirect(url_for('creator'))

        args = [provider, first_router, last_router]

        if 'provider' in request.form:
            args.insert(3, start_delay)
            script_name = "provider_serial.sh" if request.form.get("Serial Mode") else "provider.sh"
            call_script(SCRIPT_DIR, script_name, "provider", *args)
        elif 'provider_fast' in request.form:
            script_name = "provider_fast.sh"
            call_script(SCRIPT_DIR, script_name, "provider_fast", *args)

        return redirect(url_for('creator'))    
    return render_template('creator.html')

@app.route('/ping-test', methods=['GET', 'POST'])
def ping_test():
    if request.method == 'POST':
        errors = []
        provider = request.form.get("Provider", "").strip()
        routers = request.form.get("Routers", "").strip()

        if not provider or not routers:
            errors.append("At least one field was left empty!")
        elif not provider.isdigit() or not routers.isdigit():
            errors.append("At least one field was not filled with a digit!")
        elif int(provider) > 3:
            errors.append("The provider cannot be greater than 3!")
        elif int(routers) > 9:
            errors.append("The number of routers cannot be greater than 9!")

        if errors:
            for error in errors:
                flash(error, "error")
            return redirect(url_for('ping_test'))

        # Startet einen neuen Thread, um das Skript asynchron auszuführen
        threading.Thread(target=run_ping_script, args=(provider, routers)).start()  
        return redirect(url_for('ping_test'))
    return render_template('ping_test.html')

def run_ping_script(provider, router):
    # Kurze Verzögerung, damit der WebSocket-Client Zeit hat, sich zu verbinden
    time.sleep(3)  # Wartezeit in Sekunden
    # Startet das Skript und leitet die Ausgabe an SocketIO weiter
    with subprocess.Popen(['./ping.sh', provider, router], stdout=subprocess.PIPE, text=True) as process:
        for line in process.stdout:
            # Sende jede Zeile der Ausgabe an den Client
            socketio.emit('ping_output', {'data': line})

@app.route('/show-infos', methods=['GET', 'POST'])
def show_infos():
    if request.method == 'POST':
        errors = []
        provider = request.form.get("Provider", "").strip()
        router = request.form.get("Router", "").strip()

        if not provider or not router:
            errors.append("At least one field was left empty!")
        elif not provider.isdigit() or not router.isdigit():
            errors.append("At least one field was not filled with a digit!")
        elif int(provider) > 3:
            errors.append("The provider cannot be greater than 3!")
        elif int(router) > 9:
            errors.append("The router cannot be greater than 9!")

        if errors:
            for error in errors:
                flash(error, "error")
            return redirect(url_for('show_infos'))
        
        threading.Thread(target=run_show_infos_script, args=(provider, router)).start()
        return redirect(url_for('show_infos'))
    return render_template('show_infos.html')

def run_show_infos_script(provider, router):
    time.sleep(0.3)
    with subprocess.Popen(['./show_infos.sh', provider, router], stdout=subprocess.PIPE, text=True) as process:
        for line in process.stdout:
            socketio.emit('show_infos_output', {'data': line})

@app.route('/backup_restore', methods=['GET', 'POST'])
def backup_restore():
    if request.method == 'POST':
        errors = []
        if 'backup' in request.form:
            provider = request.form.get("Provider", "").strip()
            first_router = request.form.get("First Router", "").strip()
            last_router = request.form.get("Last Router", "").strip()

            if not provider or not first_router or not last_router:
                errors.append("At least one field was left empty!")
            elif not provider.isdigit() or not first_router.isdigit() or not last_router.isdigit():
                errors.append("At least one field was not filled with a digit!")
            elif int(provider) > 3:
                errors.append("The provider cannot be higher than 3!")
            elif int(first_router) > 9 or int(last_router) > 9:
                errors.append("The number of routers cannot be greater than 9!")
            elif int(first_router) > int(last_router):
                errors.append("The number of 'Last Router' cannot be smaller than the number of 'First Router'!")

            if errors:
                for error in errors:
                    flash(error, "error")
                return redirect(url_for('backup_restore'))

            script_name = "del_backup.sh" if request.form.get("delete_all") else "backup.sh"
            args = [provider, first_router, last_router]
            call_script(SCRIPT_DIR, script_name, "backup", *args)

        elif 'backup_id' in request.form:
            vm_id = request.form.get("vm_id", "").strip()

            if not vm_id:
                errors.append("Field 'VM ID' was left empty!")
            elif not vm_id.isdigit(): 
                errors.append("The 'VM ID' field must be filled with a digit!")

            if errors:
                for error in errors:
                    flash(error, "error")
                return redirect(url_for('backup_restore'))

            script_name = "del_backup_id.sh" if request.form.get("delete_all") else "backup_id.sh"
            call_script(SCRIPT_DIR, script_name, "backup_id", vm_id)

        elif 'restore' in request.form:
            provider = request.form.get("Provider", "").strip()
            first_router = request.form.get("First Router", "").strip()
            last_router = request.form.get("Last Router", "").strip()

            if not provider or not first_router or not last_router:
                errors.append("At least one field was left empty!")
            elif not provider.isdigit() or not first_router.isdigit() or not last_router.isdigit():
                errors.append("At least one field was not filled with a digit!")
            elif int(provider) > 3:
                errors.append("The provider cannot be higher than 3!")
            elif int(first_router) > 9 or int(last_router) > 9:
                errors.append("The number of routers cannot be greater than 9!")
            elif int(first_router) > int(last_router):
                errors.append("The number of 'Last Router' cannot be smaller than the number of 'First Router'!")

            if errors:
                for error in errors:
                    flash(error, "error")
                return redirect(url_for('backup_restore'))

            args = [provider, first_router, last_router]
            script_name = "restore.sh"
            call_script(SCRIPT_DIR, script_name, "restore", *args)

        elif 'restore_id' in request.form:
            vm_id = request.form.get("vm_id", "").strip()
            
            if not vm_id:
                errors.append("Field 'VM ID' was left empty!")
            elif not vm_id.isdigit(): 
                errors.append("The 'VM ID' field must be filled with a digit!")

            if errors:
                for error in errors:
                    flash(error, "error")
                return redirect(url_for('backup_restore'))

            script_name = "restore_id.sh"
            call_script(SCRIPT_DIR, script_name, "restore_id", vm_id)

        return redirect(url_for('backup_restore'))
    return render_template('backup_restore.html')

@app.route('/upgrade', methods=['GET', 'POST'])
def upgrade():
    if request.method == 'POST':
        errors = []
        
        provider = request.form.get("Provider", "").strip()
        first_router = request.form.get("First Router", "").strip()
        last_router = request.form.get("Last Router", "").strip()
        start_delay = request.form.get("Start Delay", "").strip()

        if not provider or not first_router or not last_router or ('upgrade' in request.form and not start_delay):
            errors.append("At least one field was left empty!")
        elif not provider.isdigit() or not first_router.isdigit() or not last_router.isdigit() or ('upgrade' in request.form and not start_delay.isdigit()):
            errors.append("At least one field was not filled with a digit!")
        elif int(provider) > 3:
            errors.append("The provider cannot be higher than 3!")
        elif int(first_router) > 9 or int(last_router) > 9:
            errors.append("The number of routers cannot be greater than 9!")
        elif int(first_router) > int(last_router):
            errors.append("The number of 'Last Router' cannot be smaller than the number of 'First Router'!")
        
        if errors:
            for error in errors:
                flash(error, "error")
            return redirect(url_for('upgrade'))
        
        args = [provider, first_router, last_router]
        args_fast = [provider, first_router, last_router]

        if 'upgrade' in request.form:
            args.insert(3, start_delay)
            script_name = "vyos_upgrade_serial.sh" if request.form.get("Serial Mode") else "vyos_upgrade.sh"
            call_script(SCRIPT_DIR, script_name, "upgrade", *args)
        elif 'upgrade_fast' in request.form:
            script_name = "vyos_upgrade_fast.sh"
            call_script(SCRIPT_DIR, script_name, "upgrade_fast", *args_fast)

        return redirect(url_for('upgrade'))
    return render_template('upgrade.html')

@app.route('/general', methods=['GET', 'POST'])
def general():
    errors = []
    if request.method == 'POST':
        provider = request.form.get("Provider", "").strip()
        first_router = request.form.get("First Router", "").strip()
        last_router = request.form.get("Last Router", "").strip()
        start_delay = request.form.get("Start Delay", "").strip()

        if not provider or not first_router or not last_router or (('restart' in request.form or 'start' in request.form) and not start_delay):
            errors.append("At least one field was left empty!")
        elif not provider.isdigit() or not first_router.isdigit() or not last_router.isdigit() or (('restart' in request.form or 'start' in request.form) and not start_delay.isdigit()):
            errors.append("At least one field was not filled with a digit!")
        elif int(provider) > 3:
            errors.append("The provider cannot be higher than 3!")
        elif int(first_router) > 9 or int(last_router) > 9:
            errors.append("The number of routers cannot be greater than 9!")
        elif int(first_router) > int(last_router):
            errors.append("The number of 'Last Router' cannot be smaller than the number of 'First Router'!")

        if errors:
            for error in errors:
                flash(error, "error")
            return redirect(url_for('general'))

        args = [provider, first_router, last_router]

        action = None
        if 'restart' in request.form:
            action = "restart"
            args.insert(3, start_delay)  # Start Delay hinzufügen
        elif 'start' in request.form:
            action = "start"
            args.insert(3, start_delay)
        elif 'shutdown' in request.form:
            action = "shutdown"
        elif 'destroy' in request.form:
            action = "destroy"

        if action:
            script_name = f"{action}.sh"
            call_script(GENERAL_SCRIPT_DIR, script_name, action, *args)

        return redirect(url_for('general'))
    return render_template('general.html')
