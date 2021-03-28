# silvia-pi
A Raspberry Pi modification to the Rancilio Silvia Espresso Machine implementing PID temperature control.

#### Currently Implemented Features:
* Brew temperature control
* RESTful API
* Web interface for displaying temperature and other statistics
* Programmable machine warm-up/wake-up

#### Planned Features:
* Steam temperature control
* Timed shots with pre-infusion
* Digital pressure gauge

#### Dashboard
<img src="https://github.com/brycesub/silvia-pi/blob/master/media/silvia_dashboard.gif" width=800 />

#### Hardware
* Raspberry Pi
* Power Adapter (old iPad charger)
* Micro SD Card
* Solid State Relay - For switching on and off the heating element
* Thermocouple Amplifier (e.g. MAX31855) - For interfacing between the Raspberry Pi and Thermocouple temperature probe
* Type K Thermocouple - For accurate temperature measurement
* Cables and wires

#### Hardware Installation
[Installation Instructions / Pictures](http://imgur.com/a/3WLVt)

#### GPIO Connection Table
|GPIO Pin |Destination |
|3.3 V | VCC MAX 31855K |
|Ground | Solid State Relais - |
|Ground | GND MAX 31855K |
|Ground | Main Power Switch - |
|Ground | Green Power LED - |
|GPIO 4 | Solid State Relais + |
|GPIO 8 | CS MAX 31855K |
|GPIO 9 | SO MAX 31855K |
|GPIO 11 | SCK MAX 31855K |
|GPIO 12 | Main Power Switch + |
|GPIO 16 | Green Power LED + |



#### silvia-pi Software Installation Instructions
First, install Raspbian and configure Wi-Fi and timezone.

Then, execute the following code in the pi bash shell:
````
sudo apt-get update
sudo apt-get upgrade -y
sudo apt-get install -y rpi-update git build-essential python-dev python-smbus python-pip
sudo rpi-update
sudo bash -c 'echo "dtparam=spi=on" >> /boot/config.txt'
sudo reboot
````

After the reboot:
````
sudo git clone https://github.com/brycesub/silvia-pi.git /root/silvia-pi
sudo /root/silvia-pi/setup.sh
````
This last step will download the necessariy python libraries and install the silvia-pi software in /root/silvia-pi

It also creates an entry in /etc/rc.local to start the software on every boot.

#### API Documentation

##### GET /allstats
Returns JSON of all the following statistics:
* i : Current loop iterator value (increases 10x per second)
* tempf : Temperature in °F
* avgtemp : Average temperature over the last 10 cycles (1 second) in °F
* settemp : Current set (goal) temperature in °F
* iscold : True if the temp was <120°F in the last 15 minutes
* hestat : 0 if heating element is currently off, 1 if heating element is currently on
* pidval : PID output from the last cycle
* avgpid : Average PID output over the last 10 cycles (1 second)
* pterm : PID P Term value (Proportional error)
* iterm : PID I Term value (Integral error)
* dterm : PID D Term value (Derivative error)
* snooze : Current or last snooze time, a string in the format HH:MM (24 hour)
* snoozeon : true if machine is currently snoozing, false if machine is not snoozing

##### GET /curtemp
Returns string of the current temperature in °F

##### GET /settemp
Returns string of the current set (goal) temperature in °F

##### POST /settemp
Expects one input 'settemp' with a value between 200-260.  
Sets the set (goal) temperature in °F
Returns the set temp back or a 400 error if unsuccessful.

##### GET /snooze
Returns string of the current or last snooze time formatted "HH:MM" (24 hour).  
e.g. 13:00 if snoozing until 1:00 PM local time.

##### POST /snooze
Expects one input 'snooze', a string in the format "HH:MM" (24 hour).  
This enables the snooze function, the machine will sleep until the time specified.  
Returns the snooze time set or 400 if passed an invalid input.

##### POST /resetsnooze
Disables/cancels the current snooze functionality.  
Returns true always.

##### GET /restart
Issues a reboot command to the Raspberry Pi.

##### GET /healthcheck
A simple healthcheck to see if the webserver thread is repsonding.  
Returns string 'OK'.
