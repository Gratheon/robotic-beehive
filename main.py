from time import sleep
import Jetson.GPIO as GPIO
import threading
import sys
import readchar
import select
import termios
import tty

PUL = 33  # Stepper Drive Pulses
DIR = 40  # Controller Direction Bit (High for Controller default / LOW to Force a Direction Change).
ENA = 22  # Controller Enable Bit (High to Enable / LOW to Disable).

# GPIO.setmode(GPIO.BCM)
GPIO.setmode(GPIO.BOARD) # Jetson Nano

GPIO.setup(PUL, GPIO.OUT)
GPIO.setup(DIR, GPIO.OUT)
GPIO.setup(ENA, GPIO.OUT)

print('Initialization Completed')

# Motor control parameters
delay = 0.00005  # Delay between PUL pulses - effectively sets the motor rotation speed
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
        
        sleep(0.01)  # Small delay to prevent CPU hogging

def keyboard_listener():
    """Listen for keyboard input"""
    global motor_running, direction_forward, running
    
    print("Keyboard controls:")
    print("- Press UP arrow key (↑) to move forward")
    print("- Press DOWN arrow key (↓) to move backward")
    print("- Press SPACE to stop the motor")
    print("- Press ESC or Q to exit")
    
    # Set up non-blocking keyboard input
    old_settings = termios.tcgetattr(sys.stdin)
    try:
        tty.setcbreak(sys.stdin.fileno())
        
        while running:
            # Check if there's input available
            if select.select([sys.stdin], [], [], 0.1)[0]:
                key = readchar.readkey()
                
                if key == readchar.key.UP:
                    direction_forward = True
                    motor_running = True
                    print("Up key pressed - Moving forward")
                elif key == readchar.key.DOWN:
                    direction_forward = False
                    motor_running = True
                    print("Down key pressed - Moving backward")
                elif key in (readchar.key.ESC, 'q', 'Q'):
                    print("Exiting program")
                    stop_program()
                    break
                elif key == readchar.key.SPACE:
                    motor_running = False
                    print("Space pressed - Stopping motor")
            else:
                # No key is being pressed, stop the motor
                if motor_running:
                    motor_running = False
                    print("No key pressed - Stopping motor")
    finally:
        # Restore terminal settings
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)

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

# Start keyboard listener thread
try:
    keyboard_thread = threading.Thread(target=keyboard_listener)
    keyboard_thread.daemon = True
    keyboard_thread.start()
    
    # Keep the main thread alive until keyboard_thread exits
    keyboard_thread.join()
except KeyboardInterrupt:
    stop_program()
finally:
    stop_program()

