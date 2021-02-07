# config.py
# Configuration file setting default parameters

# pin controlling heating element
pin_heat = 4
pin_mainswitch = 12
pin_powerled = 16

# brew temperature in celsius
brew_temp = 93

# on off
initial_on = False

# weak-up and sleep times
schedule = True
time_wake = '06:50'
time_sleep = '08:30'

# sample time in seconds and history in iterations
time_sample = 0.1
pid_hist_len = 25
temp_hist_len = 5

# cold PID parameters: proportional, integral and derivative
pidc_kp = 45
pidc_ki = 130
pidc_kd = 0.

# warm PID parameters: proportional, integral and derivative
pidw_kp = 33
pidw_ki = 250
pidw_kd = 40.0

# port for the web server
port = 8080
