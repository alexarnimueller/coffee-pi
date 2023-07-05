# config.py
# Configuration file setting default parameters

# pin controlling heating element
pin_heat = 4
pin_mainswitch = 12
pin_powerled = 16

# brew temperature in celsius
brew_temp = 96

# on off
initial_on = False

# weak-up and sleep times
schedule = True
time_wake = '06:45'
time_sleep = '08:15'

# sample time in seconds and history in iterations
time_sample = 0.1
pid_hist_len = 10
temp_hist_len = 10

# PID output limit
boundary = 200.

# cold PID parameters: proportional, integral and derivative
pidc_kp = 100.
pidc_ki = 0.
pidc_kd = 0.

# warm PID parameters: proportional, integral and derivative
pidw_kp = 50.
pidw_ki = 0.
pidw_kd = 10.

# port for the web server
port = 8080
