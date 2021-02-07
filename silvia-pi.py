import sys
import time
from datetime import datetime
from multiprocessing import Process, Manager
from subprocess import call
from time import sleep, time
from urllib.request import urlopen

import board
import schedule
from adafruit_max31855 import MAX31855
from busio import SPI
from digitalio import DigitalInOut
from flask import Flask, jsonify, request, render_template, abort
from gpiozero import LED, CPUTemperature, Button
from simple_pid import PID

import config

mainswitch = Button(config.pin_mainswitch)
pwr_led = LED(config.pin_powerled, initial_value=config.initial_on)


def power_loop(state):
    while True:
        mainswitch.wait_for_press()
        state['is_awake'] = not state['is_awake']
        pwr_led.toggle()


def heating_loop(state):
    heater = LED(config.pin_heat, active_high=False, initial_value=False)

    while True:
        avgpid = state['avgpid']

        if not state['is_awake']:
            state['heating'] = False
            heater.off()
            sleep(1)
        else:
            if avgpid >= 100:  # check less often when far away from brew temp
                state['heating'] = True
                heater.on()
                sleep(1)
            elif 0 < avgpid < 100:  # check more often when closer to brew temp
                state['heating'] = True
                heater.on()
                sleep(avgpid / 100.)
                heater.off()
                sleep(1 - (avgpid / 100.))
                state['heating'] = False
            else:  # turn off if temp higher than brew temp
                heater.off()
                state['heating'] = False
                sleep(1)


def pid_loop(state):
    i = 0
    pidout = 1.
    pidhist = config.pid_hist_len * [0.]
    avgpid = 0.
    temphist = config.temp_hist_len * [0.]
    temperr = config.temp_hist_len * [0]
    avgtemp = 25.
    temp = 25.
    lastsettemp = state['brewtemp']
    lasttime = time()
    iscold = True
    iswarm = False
    lastcold = 0
    lastwarm = 0

    sensor = MAX31855(SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO), DigitalInOut(board.D5))
    pid = PID(Kp=config.pidw_kp, Ki=config.pidw_ki, Kd=config.pidw_kd, setpoint=state['brewtemp'],
              sample_time=config.time_sample)

    while True:
        try:
            temp = sensor.temperature
            del temperr[0]
            temperr.append(0)
        except RuntimeError:
            del temperr[0]
            temperr.append(1)
        if sum(temperr) >= config.temp_hist_len:
            print("Temperature sensor error!")
            sys.exit()

        if i % config.temp_hist_len == 0:
            temphist.append(temp)
            del temphist[0]
            avgtemp = sum(temphist) / config.temp_hist_len

        if avgtemp <= 75:
            lastcold = i

        if avgtemp > 75:
            lastwarm = i

        if iscold and (i - lastcold) * config.time_sample > 60 * 15:
            pid.tunings = (config.pidw_kp, config.pidw_ki, config.pidw_kd)
            iscold = False

        if iswarm and (i - lastwarm) * config.time_sample > 60 * 15:
            pid.tunings = (config.pidc_kp, config.pidc_ki, config.pidc_kd)
            iscold = True

        if state['brewtemp'] != lastsettemp:
            pid.setpoint = state['brewtemp']
            lastsettemp = state['brewtemp']

        if i % config.pid_hist_len == 0:
            pidout = pid(avgtemp)
            pidhist.append(pidout)
            del pidhist[0]
            avgpid = sum(pidhist) / config.pid_hist_len

        state['i'] = i
        state['temp'] = temp
        state['iscold'] = iscold
        state['pterm'], state['iterm'], state['dterm'] = pid.components
        state['avgtemp'] = round(avgtemp, 2)
        state['pidval'] = round(pidout, 2)
        state['avgpid'] = round(avgpid, 2)

        # print(time(), state)

        sleeptime = lasttime + config.time_sample - time()
        if sleeptime < 0:
            sleeptime = 0
        sleep(sleeptime)
        i += 1
        lasttime = time()


def wakeup(state):
    state['is_awake'] = True
    pwr_led.on()


def gotosleep(state):
    state['is_awake'] = False
    pwr_led.off()


def scheduler(state):
    last_wake = 0
    last_sleep = 0
    last_sched_switch = False

    while True:
        if last_wake != state['wake_time'] or last_sleep != state['sleep_time'] or last_sched_switch != state['sched_enabled']:
            schedule.clear()

            if state['sched_enabled']:
                schedule.every().day.at(state['sleep_time']).do(gotosleep, 1, state)
                schedule.every().day.at(state['wake_time']).do(wakeup, 1, state)

                nowtm = float(datetime.now().hour) + float(datetime.now().minute) / 60.
                sleeptm = state['sleep_time'].split(":")
                sleeptm = float(sleeptm[0]) + float(sleeptm[1]) / 60.
                waketm = state['wake_time'].split(":")
                waketm = float(waketm[0]) + float(waketm[1]) / 60.

                if waketm < sleeptm:
                    if waketm <= nowtm < sleeptm:
                        wakeup(state)
                    else:
                        gotosleep(state)
                elif waketm > sleeptm:
                    if waketm > nowtm >= sleeptm:
                        gotosleep(state)
                    else:
                        wakeup(state)
            else:
                wakeup(state)

        last_wake = state['wake_time']
        last_sleep = state['sleep_time']
        last_sched_switch = state['sched_enabled']

        schedule.run_pending()
        sleep(1)


def server(state):
    app = Flask(__name__)

    # TODO: type checks

    @app.route('/')
    @app.route('/home')
    @app.route('/index')
    def index():
        return render_template("index.html")

    @app.route('/brewtemp', methods=['POST'])
    def brewtemp():
        try:
            settemp = int(request.args.get('settemp'))
            if 85 <= settemp <= 105:
                state['brewtemp'] = settemp
                return str(settemp)
            else:
                abort(400, 'Temperature out of accepted range: 85 - 105 °C!')
        except TypeError:
            abort(400, 'Invalid number for set temp.')

    @app.route('/is_awake', methods=['GET'])
    def get_is_awake():
        return str(state['is_awake'])

    @app.route('/allstats', methods=['GET'])
    def allstats():
        return jsonify(dict(state))

    @app.route('/setwake', methods=['POST'])
    def set_wake():
        wake = request.args.get('wake')
        try:
            datetime.strptime(wake, '%H:%M')
        except:
            abort(400, 'Invalid time format.')
        state['wake_time'] = wake
        return str(wake)

    @app.route('/setsleep', methods=['POST'])
    def set_sleep():
        slp = request.args.get('sleep')
        try:
            datetime.strptime(slp, '%H:%M')
        except:
            abort(400, 'Invalid time format.')
        state['sleep_time'] = slp
        return str(slp)

    @app.route('/scheduler', methods=['POST'])
    def set_sched():
        sched = request.args.get('scheduler')
        if sched == "True":
            state['sched_enabled'] = True
        else:
            state['sched_enabled'] = False
            state['is_awake'] = True
        return str(sched)

    @app.route('/turnonoff', methods=['POST'])
    def turnonoff():
        onoff = request.args.get('turnon')
        if onoff == "True":
            state['is_awake'] = True
            pwr_led.on()
        else:
            state['is_awake'] = False
            pwr_led.off()
        return str(onoff)

    @app.route('/restart')
    def restart():
        call(["reboot"])
        return 'Rebooting...'

    @app.route('/shutdown')
    def shutdown():
        call(["shutdown", "-h", "now"])
        return 'Shutting down...'

    @app.route('/healthcheck', methods=['GET'])
    def healthcheck():
        return 'OK'

    app.run(host='0.0.0.0', port=config.port)


if __name__ == "__main__":
    manager = Manager()
    pidstate = manager.dict()
    pidstate['is_awake'] = config.initial_on
    pidstate['sched_enabled'] = config.schedule
    pidstate['sleep_time'] = config.time_sleep
    pidstate['wake_time'] = config.time_wake
    pidstate['i'] = 0
    pidstate['brewtemp'] = config.brew_temp
    pidstate['avgpid'] = 0.
    cpu = CPUTemperature()

    print("Starting power button thread...")
    b = Process(target=power_loop, args=(pidstate,))
    b.daemon = True
    b.start()

    print("Starting scheduler thread...")
    s = Process(target=scheduler, args=(pidstate,))
    s.daemon = True
    s.start()

    print("Starting PID thread...")
    p = Process(target=pid_loop, args=(pidstate,))
    p.daemon = True
    p.start()

    print("Starting heat control thread...")
    h = Process(target=heating_loop, args=(pidstate,))
    h.daemon = True
    h.start()

    print("Starting server thread...")
    r = Process(target=server, args=(pidstate,))
    r.daemon = True
    r.start()

    # Start Watchdog loop
    print("Starting Watchdog...")
    piderr = 0
    weberr = 0
    cpuhot = 0
    urlhc = 'http://localhost:' + str(config.port) + '/healthcheck'

    lasti = pidstate['i']
    sleep(1)

    while b.is_alive() and p.is_alive() and h.is_alive() and r.is_alive() and s.is_alive():
        curi = pidstate['i']
        if curi == lasti:
            piderr += 1
        else:
            piderr = 0
        lasti = curi

        if piderr > 9:
            print('ERROR IN PID THREAD, RESTARTING')
            p.terminate()

        try:
            hc = urlopen(urlhc, timeout=2)
            if hc.getcode() != 200:
                weberr += 1
        except:
            weberr += 1

        if weberr > 9:
            print('ERROR IN WEB SERVER THREAD, RESTARTING')
            r.terminate()

        if cpu.temperature > 70:
            cpuhot += 1
            if cpuhot > 9:
                print("CPU TOO HOT! SHUTTING DOWN")
                call(["shutdown", "-h", "now"])

        sleep(1)
