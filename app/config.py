# config.py
# Configuration file setting default parameters

# pin controlling heating element etc.
pin_heat = 4
pin_mainswitch = 12
pin_powerled = 16

# brew temperature in degree celsius
brew_temp = 96

# weak-up and sleep times
schedule = True
time_wake = "06:50"
time_sleep = "08:30"

# sample time in seconds and history in iterations
time_sample = 0.5
pid_hist_len = 3
temp_hist_len = 10

# cold PID parameters: proportional, integral and derivative
pidc_kp = 15
pidc_ki = 0.005
pidc_kd = 40

# warm PID parameters: proportional, integral and derivative
pidw_kp = 10
pidw_ki = 0.005
pidw_kd = 40

# thresholds
pid_thresh = 50.0
cpu_threshold = 70.0

# port for the web server
port = 8080
