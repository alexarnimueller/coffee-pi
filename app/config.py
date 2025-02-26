# config.py
# Configuration file setting default parameters

# pin controlling heating element etc.
pin_heat = 4
pin_mainswitch = 12
pin_powerled = 16

# brew temperature in degree celsius
brew_temp = 94

# weak-up and sleep times
schedule = True
time_wake = "06:50"
time_sleep = "08:30"

# sample time in seconds and history in iterations
time_sample = 0.5
pid_hist_len = 5
temp_hist_len = 10

# cold PID parameters: proportional, integral and derivative
pidc_kp = 10
pidc_ki = 0
pidc_kd = 150

# warm PID parameters: proportional, integral and derivative
pidw_kp = 5
pidw_ki = 0.01
pidw_kd = 40

# thresholds
pid_thresh = 50.0
cpu_threshold = 70.0
watch_thresh = 5
delta_cold = 25

# port for the web server
port = 8080
