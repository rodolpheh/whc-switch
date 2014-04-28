# This file is part of whc-switch.
#
# SHARE YOUR PROFITS LICENSE (Revision 1):
# <houdas.rodolphe@gmail.com> and <pailleux.pierre@gmail.com> wrote this file.
# You are free to use this software, look into its code, modify it to fit your
# own needs and redistribute it. In order to commercialise it, you must give 50%
# of the profits to charities. The charities choice will be made by voters on
# Internet and the charities will receive the benefits proportionally to their
# votes quantity. If you're willing to do so, please contact us.
# Rodolphe HOUDAS and Pierre PAILLEUX.
#
# You should have received a copy of the Share Your Profits License along with
# whc-switch. If not, see above.
#
# =======================================

# Import the modules
# To manage the electronic
import RPi.GPIO as GPIO
# To get some delay (for blinking for example)
from time import sleep
# To launch system command
from os import system
# To get arguments
import sys
# To launch system command AND get the output
import subprocess
# To parse the config file
import ConfigParser


# Pin where the switch is connected.
# The switch should be connected between a GPIO and the ground.  
# GPIO __/ __ GND
spin = 7

# Pins where you should connect led in order to see wifi status
blue_led = 11
red_led = 12

# Path to configuration file
config_file = '/etc/whc-switch.conf'

# The first argument of the script should be the network device to manage
device = sys.argv[1]

# Register the state (0: client, 1: host, 2: switching)
state = 2



# Define a function to keep script running
# Arguments: None
# Return: Nothing
def loop():
  while True:
    
    # Blue led, host mode : blink
    while state == 1:
      GPIO.output(blue_led, not GPIO.input(blue_led))
      sleep(1)
    
    # Blue led, client mode : stay on
    while state == 0:
      GPIO.output(blue_led, GPIO.HIGH)
      sleep(1)
      
    # Blue led, when switching : stay off
    while state == 2:
      GPIO.output(blue_led, GPIO.LOW)
      sleep(1)

      
# Set the network depending on the switch state
# Arguments: spin (int)
# Return: Nothing
def set_network(pin=spin):
  
  # Stop interrupt, we don't want our function to be paused by a heavy-bouncing switch
  GPIO.remove_event_detect(spin)
  global state
  
  print('\nSwitch state has changed')
  print('Switch state: ' + str(GPIO.input(spin)) + ' ; Software state: ' + str(state))
  
  # If switch is on
  if not GPIO.input(spin) and not state:
    state = 2
    set_host()
    
  # If switch is off
  elif GPIO.input(spin) and state:
    state = 2
    set_client()
  
  # Now we can reset our interrupt
  GPIO.add_event_detect(spin, GPIO.RISING, callback=set_network, bouncetime=200)

 
# Set the access point (AP with hostapd)
# Arguments: None
# Return: Nothing
def set_host():
  global state
  print('')
  
  # Reset client before setting host
  reset_client()
  
  print('Setting host')
  
  # Set the ip address
  system('ip link set up dev ' + device)
  system('ip addr add 10.0.0.1/24 dev ' + device)
  
  # Start services for host mode...
  if (not start_services(['dhcpd4@' + device,'hostapd']) or not start_services(services_host) or not restart_services(services_both)) and stop_on_error:
    # ... and if one service fail, stop switching and stop all the services previously started
    state = 0
    reset_host()
    return None
  
  state = 1
  print('Host set')


# Connect to an available network  
# Arguments: None
# Return: Nothing
def set_client():
  global state
  print('')
  
  # Reset host before setting client
  reset_host()
  
  print('Setting client')
  
  # Start services for client mode...
  if (not start_services(['netctl-auto@' + device]) or not start_services(services_client) or not restart_services(services_both)) and stop_on_error:
    # ... and if one service fail, stop switching and stop all the services previously started
    state = 1
    reset_client()
    return None
  
  state = 0
  print('Client set')


# Reset the access point
# Arguments: None
# Return: Nothing
def reset_host():
  print('Resetting host')
  stop_services(services_host)
  stop_services(['hostapd','dhcpd4@' + device])
  system('ip addr flush dev ' + device)
  system('ip link set down dev ' + device)


# Disconnect from the network
# Arguments: None
# Return: Nothing
def reset_client():
  print('Resetting client')
  stop_services(services_client)
  stop_services(['netctl-auto@' + device])
  system('ip addr flush dev ' + device)
  system('ip link set down dev ' + device)


# Check service state
# Arguments: service (string)
# Return: 1 if service is active, 0 if service failed
def check_service(service):
  
  # Check if service is started
  out = subprocess.Popen('systemctl status ' + service + ' | grep Active: | cut -d":" -f2 | cut -d"(" -f1', stdout=subprocess.PIPE, shell=True).communicate()[0].strip()
  
  if out in ["inactive", "failed"]:
    GPIO.output(red_led, GPIO.HIGH)
    print('Error on service ' + service + ', check the systemd journal!')
    return 0
  elif out == "active":
    GPIO.output(red_led, GPIO.LOW)
    print('Service ' + service + ' is active!')
    return 1
  

# Map configuration section into a dictionary
# Arguments: section (string)
# Return: a dictionary
def ConfigSectionMap(section):
  dict1 = {}
  options = Config.options(section)
  for option in options:
    try:
      dict1[option] = Config.get(section, option)
      if dict1[option] == -1:
	DebugPrint("skip: %s" % option)
    except:
      print("exception on %s!" % option)
      dict1[option] = None
  return dict1


# Start services
# Arguments: services (array)
# Return: 1 if array is empty or if everything has been started without any problems, 0 if a problem has occurred
def start_services(services):
  services_states = [None] * len(services)
  index = 0
  for service in services:
    if not service:return 1
    system('systemctl start ' + service)
    services_states[index] = 0 if not check_service(service) else 1
    index = index + 1
  for service_state in services_states:
    if not service_state:
      return 0
    else:
      return 1


# Stop services
# Arguments: services (array)
# Return: Nothing
def stop_services(services):
  for service in services:
    if not service: return 1
    system('systemctl stop ' + service)
    

# Restart services
# Arguments: services(array)
# Return: 1 if array is empty or if everything has been restarted without any problems, 0 if a problem has occurred
def restart_services(services):
  services_states = [None] * len(services)
  index = 0
  for service in services:
    if not service:return 1
    system('systemctl restart ' + service)
    services_states[index] = 0 if not check_service(service) else 1
    index = index + 1
  for service_state in services_states:
    if not service_state:
      return 0
    else:
      return 1


## WE START HERE
print("Parsing configuration file...\n")

# Parse configuration file
Config = ConfigParser.ConfigParser()
Config.read(config_file)

print("== Services to manage: ==")

# Get service section
services_section = ConfigSectionMap('services')

# Get every options in arrays
services_both = services_section['both'].split(',')
services_host = services_section['host'].split(',')
services_client = services_section['client'].split(',')

# Display configuration for services
if not services_host[0]:
  print("- No services to manage when switching to host mode")
else:
  print("- Services to manage when switching to host mode:")
  for service in services_host:
    print("\t* " + service)
    
if not services_client[0]:
  print("- No services to manage when switching to client mode")
else:
  print("- Services to manage when switching to client mode:")
  for service in services_client:
    print("\t* " + service)

if not services_both[0]:
  print("- No services to manage when switching to host or client mode")
else:
  print("- Services to manage when switching to host or client mode:")
  for service in services_both:
    print("\t* " + service)
    
print("\n== Script options: ==")

# Get whc-switch section (global configuration)
whc_section = ConfigSectionMap('whc-switch')
# Since there only one option for the moment, we get it
stop_on_error = int(whc_section['stop_on_error'])

# Display global configuration
if stop_on_error:
  print("- Stop on error enabled")
else:
  print("- Stop on error disabled")

print("Setting GPIO...")

# Set pin numbering to board numbering
GPIO.setmode(GPIO.BOARD)

# Set up pin 7 as an input with pull-up resistor
GPIO.setup(spin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Set up leds
GPIO.setup(blue_led, GPIO.OUT)
GPIO.setup(red_led, GPIO.OUT)

print("Setting wifi accordingly to original state and interrupt")

# First setting of wifi
state = GPIO.input(spin)
set_network()

# Run the loop function to keep script running 
loop() 
