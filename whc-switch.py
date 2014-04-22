# Import the modules
import RPi.GPIO as GPIO
from time import sleep
from os import system
import sys
import subprocess
import ConfigParser


# Pin where the switch is connected.
# The switch should be connected between a GPIO and the ground.  
# GPIO __/ __ GND
spin = 7
blue_led = 11
red_led = 12
config_file = '/etc/whc-switch.conf'

# The first argument of the script should be the network device to manage
device = sys.argv[1]

# Register the state (0: client, 1: host)
state = 0



# Define a function to keep script running
def loop():
  while True:
    while state:
      sleep(1)
      GPIO.output(blue_led, not GPIO.input(blue_led))
    while not state:
      sleep(1)
      GPIO.output(blue_led, GPIO.HIGH)

      
# This function set the network depending on the switch state    
def set_network(pin=spin):
  GPIO.remove_event_detect(spin)
  
  print('\nSwitch state has changed')
  print('Switch state: ' + str(GPIO.input(spin)) + ' ; Software state: ' + str(state))
  
  # If switch is on
  if not GPIO.input(spin) and not state:
    set_host()
    
  # If switch is off
  elif GPIO.input(spin) and state:
    set_client()
    
  GPIO.add_event_detect(spin, GPIO.RISING, callback=set_network, bouncetime=200)

 
# Set the access point (AP with hostapd) and start gmediarender
def set_host(pin=spin):
  global state
  print('')
  
  reset_client()
  state = 1
  
  print('Setting host')
  
  system('ip link set up dev ' + device)
  system('ip addr add 10.0.0.1/24 dev ' + device)
  
  system('systemctl start dhcpd4')
  if not check_service('dhcpd4') and stop_on_error:
    reset_host()
    return None
  
  system('systemctl start hostapd')
  if not check_service('hostapd') and stop_on_error:
    reset_host()
    return None
  
  if not start_services('host') and stop_on_error:
    reset_host()
    return None
  
  if not restart_services('both') and stop_on_error:
    reset_host()
    return None
  
  print('Host set')


# Connect to an available network  
def set_client(pin=spin):
  global state
  print('')
  
  reset_host()
  state = 0
  
  print('Setting client')
  
  system('systemctl start netctl-auto@' + device)
  
  if not check_service('netctl-auto@' + device):
    reset_client()
    return None

  if not start_services('client') and stop_on_error:
    reset_client()
    return None
  
  if not restart_services('both') and stop_on_error:
    reset_client()
    return None
  
  print('Client set')


# Reset the access point and stop gmediarender  
def reset_host(pin=spin):
  print('Resetting host')
  stop_services('host')
  system('systemctl stop hostapd')
  system('systemctl stop dhcpd4')
  system('ip addr flush dev ' + device)
  system('ip link set down dev ' + device)


# Disconnect from the network  
def reset_client(pin=spin):
  print('Resetting client')
  stop_services('client')
  system('systemctl stop netctl-auto@' + device)
  system('ip addr flush dev ' + device)
  system('ip link set down dev ' + device)


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


def start_services(services):
  
  for service in services:
    system('systemctl start ' + service)
    
    if not check_service(service):
      return 0
    else:
      return 1
    

def stop_services(services):
  
  for service in services:
    system('systemctl stop ' + service)
    

def reset_services(services):
  
  for service in services:
    system('systemctl restart ' + service)
    
    if not check_service(service):
      return 0
    else:
      return 1

print("Parsing configuration file...\n")

Config = ConfigParser.ConfigParser()
Config.read(config_file)

print("== Services to manage: ==")

services_section = ConfigSectionMap('services')

services_both = services_section['both'].split(',')
services_host = services_section['host'].split(',')
services_client = services_section['client'].split(',')

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

whc_section = ConfigSectionMap('whc-switch')
stop_on_error = int(services_section['stop_on_error'])

if stop_on_error:
  print("- Stop on error enabled")
else:
  print("- Stop on error disabled")

print("Setting GPIO...")

# Set pin numbering to board numbering
GPIO.setmode(GPIO.BOARD)

# Set up pin 7 as an input with pull-up resistor
GPIO.setup(spin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Set up outputs
GPIO.setup(blue_led, GPIO.OUT)
GPIO.setup(red_led, GPIO.OUT)

# First setting of wifi
print("Setting wifi accordingly to original state and interrupt")
state = GPIO.input(spin)
set_network()

# Run the loop function to keep script running 
loop() 
