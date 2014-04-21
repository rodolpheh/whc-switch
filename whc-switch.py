# Import the modules
import RPi.GPIO as GPIO
from time import sleep
from os import system
import sys
import subprocess

# Pin where the switch is connected.
# The switch should be connected between a GPIO and the ground.  
# GPIO __/ __ GND
fpin = 7
blue_led = 11
red_led = 12

# The first argument of the script should be the network device to manage
device = sys.argv[1]

# Register the state (0: client, 1: host)
state = 0

# Define a function to keep script running
def loop():
  if state:
    while True:
      GPIO.output(blue_led, GPIO.HIGH)
      sleep(600)
  else:
    while True:
      sleep(1)
      GPIO.output(blue_led, not GPIO.input(blue_led))
      

# This function set the network depending on the switch state    
def set_network(pin=fpin):
  global state
  print('\nSwitch state has changed')
  print('Switch state: ' + str(GPIO.input(fpin)) + ' ; Software state: ' + str(state))
  # If switch is on
  if not GPIO.input(fpin) and not state:
    set_host()
    state = 1
  # If switch is off
  elif GPIO.input(fpin) and state:
    set_client()
    state = 0
 
# Set the access point (AP with hostapd) and start gmediarender
def set_host(pin=fpin):
  print('')
  reset_client()
  print('Setting host')
  system('ip link set up dev ' + device)
  system('ip addr add 10.0.0.1/24 dev ' + device)
  
  system('systemctl start dhcpd4')
  if !check_service('dhcpd4'):
    reset_host()
    return None
  
  system('systemctl start hostapd')
  if !check_service('hostapd'):
    reset_host()
    return None
  
  print('Host set')

# Connect to an available network  
def set_client(pin=fpin):
  print('')
  reset_host()
  print('Setting client')
  system('systemctl start netctl-auto@' + device)
  if check_service('netctl-auto@' + device):
    print('Client set')

# Reset the access point and stop gmediarender  
def reset_host(pin=fpin):
  print('Resetting host')
  system('systemctl stop hostapd')
  system('systemctl stop dhcpd4')
  system('ip addr flush dev ' + device)
  system('ip link set down dev ' + device)

# Disconnect from the network  
def reset_client(pin=fpin):
  print('Resetting client')
  system('systemctl stop netctl-auto@' + device)
  system('ip addr flush dev ' + device)
  system('ip link set down dev ' + device)
  
def get_state():
  state = 0 if GPIO.input(fpin) else 1
  return state

def check_service(service):
  # Check if service is started
  out = subprocess.Popen('systemctl status ' + service + ' | grep Active: | cut -d":" -f2 | cut -d"(" -f1', stdout=subprocess.PIPE, shell=True).communicate()[0].strip()
  if out == "inactive":
    GPIO.output(red_led, GPIO.HIGH)
    print('Error on service ' + service + ', check the systemd journal!')
    return 0
  elif out == "active":
    GPIO.output(red_led, GPIO.LOW)
    print('Service ' + service + ' is active!')
    return 1

print("Setting GPIO...")

# Set pin numbering to board numbering
GPIO.setmode(GPIO.BOARD)
# Set up pin 7 as an input with pull-up resistor
GPIO.setup(fpin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
# Set up outputs
GPIO.setup(blue_led, GPIO.OUT)
GPIO.setup(red_led, GPIO.OUT)

print("Setting wifi accordingly to original state")

state = GPIO.input(fpin)
set_network()

print("Setting interrupt...")

# Add event on rising and falling edge
GPIO.add_event_detect(fpin, GPIO.RISING, callback=set_network, bouncetime=200)

# Run the loop function to keep script running 
loop() 
