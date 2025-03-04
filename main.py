from time import sleep
import Jetson.GPIO as GPIO
from pynput import keyboard
import threading
import sys

PUL = 33  # Stepper Drive Pulses
DIR = 40  # Controller Direction Bit (High for Controller default / LOW to Force a Direction Change).
ENA = 22  # Controller Enable Bit (High to Enable / LOW to Disable).

GPIO.setmode(GPIO.BCM)
# GPIO.setmode(GPIO.BOARD) # Do NOT use GPIO.BOARD mode. Here for comparison only. 

GPIO.setup(PUL, GPIO.OUT)
GPIO.setup(DIR, GPIO.OUT)
GPIO.setup(ENA, GPIO.OUT)

print('Initialization Completed')

# Motor control parameters
delay = 0.0005  # Delay between PUL pulses - effectively sets the motor rotation speed
print('Speed set to ' + str(delay))

# Control flags
running = True
motor_running = False
direction_forward = True

def pulse_motor():
    """Function to continuously pulse the motor while motor_running is True"""
    global motor_running, direction_forward
    
    while running:
        if motor_running:
            # Set direction
            if direction_forward:
                GPIO.output(DIR, GPIO.LOW)
                print('Moving Forward')
            else:
                GPIO.output(DIR, GPIO.HIGH)
                print('Moving Backward')
            
            # Enable motor
            GPIO.output(ENA, GPIO.HIGH)
            
            # Pulse the motor as long as motor_running is True
            while motor_running and running:
                GPIO.output(PUL, GPIO.HIGH)
                sleep(delay)
                GPIO.output(PUL, GPIO.LOW)
                sleep(delay)
            
            # Disable motor when stopped
            GPIO.output(ENA, GPIO.LOW)
        
        sleep(0.1)  # Small delay to prevent CPU hogging

def on_press(key):
    """Handle key press events"""
    global motor_running, direction_forward
    
    try:
        if key == keyboard.Key.up:
            direction_forward = True
            motor_running = True
            print("Up key pressed - Moving forward")
        elif key == keyboard.Key.down:
            direction_forward = False
            motor_running = True
            print("Down key pressed - Moving backward")
        elif key == keyboard.Key.esc:
            print("Exiting program")
            stop_program()
            return False  # Stop listener
    except AttributeError:
        pass

def on_release(key):
    """Handle key release events"""
    global motor_running
    
    try:
        if key == keyboard.Key.up or key == keyboard.Key.down:
            motor_running = False
            print("Key released - Stopping motor")
    except AttributeError:
        pass

def stop_program():
    """Clean up and exit the program"""
    global running
    running = False
    motor_running = False
    print("Cleaning up GPIO")
    GPIO.cleanup()
    print("Exiting program")

# Start the motor control thread
motor_thread = threading.Thread(target=pulse_motor)
motor_thread.daemon = True
motor_thread.start()

print("Keyboard controls:")
print("- Press UP arrow key to move forward")
print("- Press DOWN arrow key to move backward")
print("- Press ESC to exit")

# Start keyboard listener
try:
    with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        listener.join()
except KeyboardInterrupt:
    stop_program()
finally:
    stop_program()

