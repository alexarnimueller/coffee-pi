# config.py
# Configuration file setting default parameters

# pin controlling heating element etc.
pin_heat = 4
pin_mainswitch = 12
pin_powerled = 16

# brew temperature in degree celsius
brew_temp = 93

# weak-up and sleep times
schedule = False
time_wake = "06:50"
time_sleep = "08:30"

# sample time in seconds and history in iterations
time_sample = 0.3
pid_hist_len = 10
temp_hist_len = 5

# cold PID parameters: proportional, integral and derivative
pidc_kp = 3
pidc_ki = 0.01
pidc_kd = 40

# warm PID parameters: proportional, integral and derivative
pidw_kp = 3
pidw_ki = 0.01
pidw_kd = 40

pid_thresh = 100.0

# port for the web server
port = 8080
