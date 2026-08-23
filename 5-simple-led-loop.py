from gpiozero import LED
from time import sleep
from signal import pause

i = 0
led = LED(16) # initialize the pin
led.on()

while i<5:
        led.toggle() #toggle the slides on and off
        i = i+1 #increment variable by one
        sleep(1) #sleep for 100 ms

pause() #keep program running
