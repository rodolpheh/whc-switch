# Import the modules
import RPi.GPIO as gpio
from time import sleep
from os import system
import sys

# Pin where the switch is connected.
# The switch should be connected between a GPIO and the ground.  
# GPIO __/ __ GND
spin = 7

# The first argument of the script should be the network device to manage
device = sys.argv[1]

# Define a function to keep script running
def loop():
  while True:
    sleep(600)

# This function set the network depending on the switch state    
def set_network(pin=spin):
  print('')
  # If switch is on
  if gpio.input(pin):
    set_host()
  # If switch is off
  else:
    set_client()
 
# Set the access point (AP with hostapd) and start gmediarender
def set_host(pin=spin):
  reset_client()
  print('Setting host')
  system('ip link set up dev ' + device)
  system('ip addr add 10.0.0.1/24 dev ' + device)
  system('systemctl start dhcpd4')
  system('systemctl start hostapd')
  system('systemctl start gmediarender')

# Connect to an available network  
def set_client(pin=spin):
  reset_host()
  print('Setting client')
  system('systemctl start netctl-auto@' + device)

# Reset the access point and stop gmediarender  
def reset_host(pin=spin):
  print('Resetting host')
  system('systemctl stop gmediarender')
  system('systemctl stop hostapd')
  system('systemctl stop dhcpd4')
  system('ip addr flush dev ' + device)
  system('ip link set down dev ' + device)

# Disconnect from the network  
def reset_client(pin=spin):
  print('Resetting client')
  system('systemctl stop netctl-auto@' + device)
  system('ip addr flush dev ' + device)
  system('ip link set down dev ' + device)

print("Setting GPIO...")

# Set pin numbering to board numbering
gpio.setmode(gpio.BOARD)
# Set up pin 7 as an input with pull-up resistor
gpio.setup(spin, gpio.IN, pull_up_down=gpio.PUD_UP)

print("Setting wifi accordingly to original state")

set_network(spin);

print("Setting interrupt...")

# Add an event on a rising or falling edge
gpio.add_event_detect(spin, gpio.BOTH, callback=set_network, bouncetime=200)

# Run the loop function to keep script running 
loop() 
