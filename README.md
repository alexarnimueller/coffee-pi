# coffee-pi
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
--- | --- |
|3.3 V|VCC MAX 31855K |
|Ground| Solid State Relais - |
|Ground| GND MAX 31855K |
|Ground| Main Power Switch - |
|Ground| Green Power LED - |
|GPIO 4| Solid State Relais + |
|GPIO 8| CS MAX 31855K |
|GPIO 9| SO MAX 31855K |
|GPIO 11| SCK MAX 31855K |
|GPIO 12| Main Power Switch + |
|GPIO 16| Green Power LED + |



#### coffee-pi Software Installation Instructions
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

Then install berryconda3 (change the default directory to `/home/pi/miniconda3`):
````
wget https://github.com/jjhelmus/berryconda/releases/download/v2.0.0/Berryconda3-2.0.0-Linux-armv7l.sh
sudo /bin/bash Berryconda3-2.0.0-Linux-armv7l.sh
````

After a reboot, clone the coffee-pi repo:
````
git clone https://github.com/alexarnimueller/coffee-pi.git /home/pi/coffee-pi
cd /home/pi/coffee-pi
````

Then run the following command to create a new conda environment and install the necessary packages:
````
conda create env -f environment.yml
pip install poetry
poetry install
````

Finally, edit your crontab to run the coffee-pi script at reboot by typing `crontab -e` and adding the following line at the bottom of the file:
````
@reboot /home/pi/miniconda3/envs/coffee-pi/bin/python /home/pi/coffee-pi/app/app.py
````

#### API Documentation

##### GET /allstats


##### GET /brewtemp
Returns the current brew temperature in °C

##### POST /brewtemp
Sets the desired brew temperature in °C

##### GET /scheduler/{on,off}
Turns the scheduler on or off

##### GET /restart
Issues a reboot command to the Raspberry Pi.

##### GET /turnon

##### GET /turnoff

##### GET /healthcheck
A simple healthcheck to see if the webserver thread is repsonding.  
Returns string 'OK'.

