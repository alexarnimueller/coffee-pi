import sys
import time
from datetime import datetime
from multiprocessing import Process, Manager
from subprocess import call
from time import sleep

from urllib.request import urlopen
import logging
from logging.handlers import WatchedFileHandler

import board
import schedule
from adafruit_max31855 import MAX31855
from busio import SPI
from digitalio import DigitalInOut
from flask import Flask, flash, redirect, jsonify, request, render_template, abort
from gpiozero import LED, CPUTemperature, Button
from simple_pid import PID

import config as config


def log_setup():
    log_handler = WatchedFileHandler("run.log")
    formatter = logging.Formatter("%(asctime)s  - %(levelname)s - %(message)s", "%d-%b-%y %H:%M:%S")
    formatter.converter = time.gmtime  # if you want UTC time
    log_handler.setFormatter(formatter)
    logger = logging.getLogger()
    logger.addHandler(log_handler)
    logger.setLevel(logging.INFO)


def switch_loop(state):
    mainswitch = Button(config.pin_mainswitch, pull_up=True)
    while True:
        mainswitch.wait_for_press()
        state["is_awake"] = not state["is_awake"]
        sleep(config.time_sample)


def main_loop(state):
    def wakeup(state):
        state["is_awake"] = True

    def gotosleep(state):
        state["is_awake"] = False

    i = 0
    pidout = 1.0
    avgpid = 0.0
    pidhist = config.pid_hist_len * [0.0]
    temphist = config.temp_hist_len * [0.0]
    temperr = config.temp_hist_len * [0]
    avgtemp = 25.0
    temp = 25.0
    lastsettemp = state["brewtemp"]
    last_wake = 0
    last_sleep = 0
    last_sched_switch = False

    cpu_t = CPUTemperature()
    heater = LED(config.pin_heat, active_high=True, initial_value=False)
    pwr_led = LED(config.pin_powerled, initial_value=False)
    spi = SPI(board.SCLK, MOSI=board.MOSI, MISO=board.MISO)
    cs = DigitalInOut(board.D5)
    sensor = MAX31855(spi, cs)
    pid = PID(
        Kp=config.pidc_kp,
        Ki=config.pidc_ki,
        Kd=config.pidc_kd,
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
            logging.error("TEMPERATURE SENSOR ERROR!")
            state["is_awake"] = False  # turn off
            sys.exit()

        temphist.append(temp)
        del temphist[0]
        avgtemp = sum(temphist) / config.temp_hist_len

        if state["brewtemp"] != lastsettemp:
            pid.setpoint = state["brewtemp"]
            lastsettemp = state["brewtemp"]

        # check if work to do
        if not state["is_awake"]:
            heater.off()
            pwr_led.off()
            state["heating"] = False
            sleep(config.time_sample)

        else:
            pwr_led.on()
            # PID logic
            if avgtemp > pid.setpoint - 25:
                pid.tunings = (config.pidw_kp, config.pidw_ki, config.pidw_kd)
            else:
                pid.tunings = (config.pidc_kp, config.pidc_ki, config.pidc_kd)

            pidout = pid(avgtemp)
            pidhist.append(pidout)
            del pidhist[0]
            avgpid = sum(pidhist) / config.pid_hist_len

            # heating logic
            if avgpid >= config.pid_thresh:  # check less often when far away from brew temp
                heater.on()
                state["heating"] = True
                sleep(config.time_sample)
            elif 0 < avgpid < config.pid_thresh:  # check more often when closer to brew temp
                heater.on()
                state["heating"] = True
                sleep(config.time_sample * float(avgpid / config.pid_thresh))
                heater.off()
                state["heating"] = False
                sleep(max(0.01, config.time_sample * (1.0 - (avgpid / config.pid_thresh))))
            else:  # turn off if temp higher than brew temp
                heater.off()
                state["heating"] = False
                sleep(config.time_sample)

        state["i"] = i
        state["temp"] = temp
        state["pterm"], state["iterm"], state["dterm"] = pid.components
        state["avgtemp"] = round(avgtemp, 3)
        state["pidval"] = round(pidout, 3)
        state["avgpid"] = round(avgpid, 3)
        state["cpu"] = cpu_t.temperature
        i += 1

        # Scheduler
        if (
            last_wake != state["wake_time"]
            or last_sleep != state["sleep_time"]
            or last_sched_switch != state["sched_enabled"]
        ):
            schedule.clear()

            if state["sched_enabled"]:
                schedule.every().day.at(state["sleep_time"]).do(gotosleep, state)
                schedule.every().day.at(state["wake_time"]).do(wakeup, state)

                nowtm = float(datetime.now().hour) + float(datetime.now().minute) / 60.0
                sleeptm = state["sleep_time"].split(":")
                sleeptm = float(sleeptm[0]) + float(sleeptm[1]) / 60.0
                waketm = state["wake_time"].split(":")
                waketm = float(waketm[0]) + float(waketm[1]) / 60.0

                if waketm < sleeptm:
                    if waketm <= nowtm < sleeptm:
                        state["is_awake"] = True
                        pid.tunings = (config.pidc_kp, config.pidc_ki, config.pidc_kd)
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


def server(state):
    app = Flask(__name__)
    log = logging.getLogger("werkzeug")
    log.setLevel(logging.WARNING)

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/brewtemp", methods=["GET", "POST"])
    def brewtemp():
        if request.method == "POST":
            temp = float(request.form["settemp"])
            if 90.0 < temp < 100.0:
                state["brewtemp"] = temp
            else:
                flash(f"{temp}°C is outside the accepted range of 90-100 °C!")
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
        scdlr = request.form.get("scheduler")
        if scdlr == "on":
            state["sched_enabled"] = True
        else:
            state["sched_enabled"] = False
        return f"Scheduler is {scdlr}"

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
    log_setup()
    manager = Manager()
    statedict = manager.dict()
    statedict["is_awake"] = False
    statedict["heating"] = False
    statedict["sched_enabled"] = config.schedule
    statedict["sleep_time"] = config.time_sleep
    statedict["wake_time"] = config.time_wake
    statedict["brewtemp"] = config.brew_temp
    statedict["avgpid"] = 0.0
    statedict["i"] = 0
    piderr = 0
    weberr = 0
    cpuhot = 0
    urlhc = "http://localhost:" + str(config.port) + "/healthcheck"
    urloff = "http://localhost:" + str(config.port) + "/turnoff"

    logging.info("Starting PID thread...")
    p = Process(target=main_loop, args=(statedict,))
    p.start()

    logging.info("Starting server thread...")
    r = Process(target=server, args=(statedict,))
    r.start()

    logging.info("Starting power button thread...")
    b = Process(target=switch_loop, args=(statedict,))
    b.start()

    logging.info("Starting Watchdog...")
    lasti = statedict["i"]
    sleep(config.watch_thresh * config.time_sample)

    while True:
        if not b.is_alive():
            b.join()
            b.terminate()
            logging.warning("Power button thread off, restarting...")
            b = Process(target=switch_loop, args=(statedict,))
            b.start()

        if not p.is_alive():
            p.join()
            p.terminate()
            logging.warning("PID thread off, restarting...")
            p = Process(target=main_loop, args=(statedict,))
            p.start()

        if not r.is_alive():
            r.join()
            r.terminate()
            logging.warning("Server thread off, restarting...")
            r = Process(target=server, args=(statedict,))
            r.start()

        curi = statedict["i"]
        if curi == lasti:
            piderr += 1
        else:
            piderr = 0

        try:
            hc = urlopen(urlhc)
            if hc.getcode() != 200:
                weberr += 1
        except:
            weberr += 1

        if statedict["cpu"] > config.cpu_threshold:
            cpuhot += 1

        if cpuhot > config.watch_thresh:
            logging.error("CPU TOO HOT! SHUTTING DOWN")
            resp = urlopen(urloff)
            call(["shutdown", "-h", "now"])

        elif piderr > config.watch_thresh:
            logging.error("ERROR IN PID THREAD, RESTARTING")
            logging.info("Restarting...")
            resp = urlopen(urloff)
            call(["reboot", "now"])

        elif weberr > config.watch_thresh:
            logging.error("ERROR IN WEB SERVER THREAD, RESTARTING")
            logging.info("Restarting...")
            resp = urlopen(urloff)
            call(["reboot", "now"])

        lasti = curi
        sleep(config.watch_thresh * config.time_sample)
