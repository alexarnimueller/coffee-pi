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
time_sample = 0.5
pid_hist_len = 20
temp_hist_len = 10

# cold PID parameters: proportional, integral and derivative
pidc_kp = 3.4
pidc_ki = 0.3
pidc_kd = 40.0

# warm PID parameters: proportional, integral and derivative
pidw_kp = 2.9
pidw_ki = 0.3
pidw_kd = 40.0

# port for the web server
port = 8080
