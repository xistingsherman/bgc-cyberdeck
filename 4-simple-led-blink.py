from gpiozero import LED
from signal import pause

led = LED(16) # initialize the pin
led.on() # turn the pin on
pause() # keeps the program on
