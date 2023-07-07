import sys
import time
from datetime import datetime
from multiprocessing import Process, Manager
from subprocess import call
from time import sleep, time

# from urllib.request import urlopen
import logging

import board
import schedule
from adafruit_max31855 import MAX31855
from busio import SPI
from digitalio import DigitalInOut
from flask import Flask, flash, redirect, jsonify, request, render_template, abort
from gpiozero import LED, CPUTemperature, Button
from simple_pid import PID

import config as config

logging.basicConfig(
    filename="run.log",
    filemode="a",
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%d-%b-%y %H:%M:%S",
    level=logging.DEBUG,
)


def power_loop(state):
    mainswitch = Button(config.pin_mainswitch)
    pwr_led = LED(config.pin_powerled, initial_value=False)

    if state["is_awake"]:
        pwr_led.on()
    else:
        pwr_led.off()

    while True:
        mainswitch.wait_for_press()
        state["is_awake"] = not state["is_awake"]
        pwr_led.toggle()


def heating_loop(state):
    heater = LED(config.pin_heat, active_high=True, initial_value=False)

    while True:
        avgpid = state["avgpid"]

        logging.debug(f'Awake: {state["is_awake"]}, Heating: {state["heating"]}, Heater: {heater.is_active}')

        if not state["is_awake"]:
            state["heating"] = False
            heater.off()
            sleep(1)
        else:
            if avgpid >= 100:  # check less often when far away from brew temp
                state["heating"] = True
                heater.on()
                sleep(1)
            elif 0 < avgpid < 100:  # check more often when closer to brew temp
                state["heating"] = True
                heater.on()
                sleep(avgpid / 100.0)
                heater.off()
                state["heating"] = False
                sleep(1 - (avgpid / 100.0))
            else:  # turn off if temp higher than brew temp
                state["heating"] = False
                heater.off()
                sleep(1)


def pid_loop(state):
    i = 0
    pidout = 1.0
    pidhist = config.pid_hist_len * [0.0]
    avgpid = 0.0
    temphist = config.temp_hist_len * [0.0]
    temperr = config.temp_hist_len * [0]
    avgtemp = 25.0
    temp = 25.0
    lastsettemp = state["brewtemp"]
    lasttime = time()
    iscold = True
    iswarm = False
    lastcold = 0
    lastwarm = 0

    spi = SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)
    cs = DigitalInOut(board.D5)
    sensor = MAX31855(spi, cs)
    pid = PID(
        Kp=config.pidw_kp,
        Ki=config.pidw_ki,
        Kd=config.pidw_kd,
        setpoint=state["brewtemp"],
        sample_time=config.time_sample,
    )

    while True:
        try:
            temp = sensor.temperature
            del temperr[0]
            temperr.append(0)
        except:
            del temperr[0]
            temperr.append(1)
        if sum(temperr) >= config.temp_hist_len:
            logging.error("Temperature sensor error!")
            sys.exit()

        if i % config.temp_hist_len == 0:
            temphist.append(temp)
            del temphist[0]
            avgtemp = sum(temphist) / config.temp_hist_len

        if avgtemp <= 70:
            lastcold = i

        if avgtemp > 70:
            lastwarm = i

        if iscold and (i - lastcold) * config.time_sample > 60 * 15:
            pid.tunings = (config.pidw_kp, config.pidw_ki, config.pidw_kd)
            iscold = False

        if iswarm and (i - lastwarm) * config.time_sample > 60 * 15:
            pid.tunings = (config.pidc_kp, config.pidc_ki, config.pidc_kd)
            iscold = True

        if state["brewtemp"] != lastsettemp:
            pid.setpoint = state["brewtemp"]
            lastsettemp = state["brewtemp"]

        if i % config.pid_hist_len == 0:
            pidout = pid(avgtemp)
            pidhist.append(pidout)
            del pidhist[0]
            avgpid = sum(pidhist) / config.pid_hist_len

        state["i"] = i
        state["temp"] = temp
        state["iscold"] = iscold
        state["pterm"], state["iterm"], state["dterm"] = pid.components
        state["avgtemp"] = round(avgtemp, 2)
        state["pidval"] = round(pidout, 2)
        state["avgpid"] = round(avgpid, 2)

        logging.info({k: v for k, v in state.items()})

        sleeptime = lasttime + config.time_sample - time()
        if sleeptime < 0:
            sleeptime = 0
        sleep(sleeptime)
        i += 1
        lasttime = time()


def scheduler(state):
    def wakeup(state):
        state["is_awake"] = True

    def gotosleep(state):
        state["is_awake"] = False

    last_wake = 0
    last_sleep = 0
    last_sched_switch = False

    while True:
        if (
            last_wake != state["wake_time"]
            or last_sleep != state["sleep_time"]
            or last_sched_switch != state["sched_enabled"]
        ):
            schedule.clear()

            if state["sched_enabled"]:
                schedule.every().day.at(state["sleep_time"]).do(gotosleep, 1, state)
                schedule.every().day.at(state["wake_time"]).do(wakeup, 1, state)

                nowtm = float(datetime.now().hour) + float(datetime.now().minute) / 60.0
                sleeptm = state["sleep_time"].split(":")
                sleeptm = float(sleeptm[0]) + float(sleeptm[1]) / 60.0
                waketm = state["wake_time"].split(":")
                waketm = float(waketm[0]) + float(waketm[1]) / 60.0

                if waketm < sleeptm:
                    if waketm <= nowtm < sleeptm:
                        state["is_awake"] = True
                    else:
                        state["is_awake"] = False
                elif waketm > sleeptm:
                    if waketm > nowtm >= sleeptm:
                        state["is_awake"] = False
                    else:
                        state["is_awake"] = True

        last_wake = state["wake_time"]
        last_sleep = state["sleep_time"]
        last_sched_switch = state["sched_enabled"]

        schedule.run_pending()
        sleep(1)


def server(state):
    app = Flask(__name__)

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/brewtemp", methods=["GET", "POST"])
    def brewtemp():
        if request.method == "POST":
            temp = request.form["settemp"]
            if 90.0 < temp < 100.0:
                state["brewtemp"] = temp
            else:
                flash(f"{temp}°C is outside the accepted range!")
            return redirect("/")

        else:
            return jsonify({"temp": state["brewtemp"]})

    @app.route("/is_awake", methods=["GET"])
    def get_is_awake():
        return str(state["is_awake"])

    @app.route("/allstats", methods=["GET"])
    def allstats():
        return jsonify({k: v for k, v in state.items()})

    @app.route("/scheduler", methods=["POST"])
    def set_scheduler():
        enable = request.form.get("enable")
        logging.debug(f"Schedule enabled: {enable}")
        state["sched_enabled"] = enable
        return {"scheduler": enable}

    @app.route("/setwake", methods=["POST"])
    def set_wake():
        wake = request.form.get("wake")
        try:
            datetime.strptime(wake, "%H:%M")
        except:
            abort(400, "Invalid time format.")
        state["wake_time"] = wake
        return str(wake)

    @app.route("/setsleep", methods=["POST"])
    def set_sleep():
        sleep = request.form.get("sleep")
        try:
            datetime.strptime(sleep, "%H:%M")
        except:
            abort(400, "Invalid time format.")
        state["sleep_time"] = sleep
        return str(sleep)

    @app.route("/turnon", methods=["GET"])
    def turnon():
        state["is_awake"] = True
        return "ON"

    @app.route("/turnoff", methods=["GET"])
    def turnoff():
        state["is_awake"] = False
        return "OFF"

    @app.route("/restart")
    def restart():
        call(["reboot"])
        return "Rebooting..."

    @app.route("/shutdown")
    def shutdown():
        call(["shutdown", "-h", "now"])
        return "Shutting down..."

    @app.route("/healthcheck", methods=["GET"])
    def healthcheck():
        return "OK"

    app.run(host="0.0.0.0", port=config.port)


if __name__ == "__main__":
    manager = Manager()
    pidstate = manager.dict()
    pidstate["is_awake"] = False
    pidstate["heating"] = False
    pidstate["sched_enabled"] = config.schedule
    pidstate["sleep_time"] = config.time_sleep
    pidstate["wake_time"] = config.time_wake
    pidstate["i"] = 0
    pidstate["brewtemp"] = config.brew_temp
    pidstate["avgpid"] = 0.0

    logging.info("Starting power button thread...")
    b = Process(target=power_loop, args=(pidstate,))
    # b.daemon = True
    b.start()

    logging.info("Starting scheduler thread...")
    s = Process(target=scheduler, args=(pidstate,))
    # s.daemon = True
    s.start()

    logging.info("Starting PID thread...")
    p = Process(target=pid_loop, args=(pidstate,))
    # p.daemon = True
    p.start()

    logging.info("Starting heat control thread...")
    h = Process(target=heating_loop, args=(pidstate,))
    # h.daemon = True
    h.start()

    logging.info("Starting server thread...")
    r = Process(target=server, args=(pidstate,))
    # r.daemon = True
    r.start()

    # Start Watchdog loop
    logging.info("Starting Watchdog...")
    piderr = 0
    weberr = 0
    cpuhot = 0
    cpu_t = CPUTemperature()
    urlhc = "http://localhost:" + str(config.port) + "/healthcheck"

    lasti = pidstate["i"]
    sleep(1)

    while b.is_alive() and p.is_alive() and h.is_alive() and r.is_alive() and s.is_alive():
        curi = pidstate["i"]
        if curi == lasti:
            piderr += 1
        else:
            piderr = 0
        lasti = curi

        if piderr > 9:
            logging.error("ERROR IN PID THREAD, RESTARTING")
            p.terminate()

        # try:
        #     hc = urlopen(urlhc, timeout=10)
        #     if hc.getcode() != 200:
        #         weberr += 1
        # except:
        #     weberr += 1
        #
        # if weberr > 9:
        #     logging.error("ERROR IN WEB SERVER THREAD, RESTARTING")
        #     r.terminate()

        if cpu_t.temperature > 75:
            cpuhot += 1
            if cpuhot > 29:
                logging.error("CPU TOO HOT! SHUTTING DOWN")
                call(["shutdown", "-h", "now"])

        sleep(1)
