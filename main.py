from time import sleep
import Jetson.GPIO as GPIO
import threading
import sys
import readchar
import select

# GPIO pin definitions
PUL = 33  # Stepper Drive Pulses
DIR = 40  # Controller Direction Bit
ENA = 22  # Controller Enable Bit

# Control flags
running = True
motor_running = False
direction_forward = True

def setup_gpio():
    """Initialize GPIO pins"""
    GPIO.setmode(GPIO.BOARD)  # Jetson Nano
    GPIO.setup(PUL, GPIO.OUT)
    GPIO.setup(DIR, GPIO.OUT)
    GPIO.setup(ENA, GPIO.OUT)
    print('Initialization Completed')

def set_motor_direction(forward=True):
    """Set the motor direction"""
    global direction_forward
    direction_forward = forward
    if forward:
        GPIO.output(DIR, GPIO.HIGH)
        print('Moving Forward')
    else:
        GPIO.output(DIR, GPIO.LOW)
        print('Moving Backward')

def start_motor():
    """Start the motor"""
    global motor_running
    motor_running = True
    GPIO.output(ENA, GPIO.HIGH)

def stop_motor():
    """Stop the motor"""
    global motor_running
    motor_running = False
    GPIO.output(ENA, GPIO.LOW)
    print("Motor stopped")

def pulse_motor():
    """Function to continuously pulse the motor while motor_running is True"""
    global motor_running, direction_forward
    delay = 0.00005  # Delay between PUL pulses - effectively sets the motor rotation speed
    print('Speed set to ' + str(delay))
    
    while running:
        if motor_running:
            # Set direction based on current setting
            set_motor_direction(direction_forward)
            
            # Enable motor
            GPIO.output(ENA, GPIO.HIGH)
            
            # Pulse the motor as long as motor_running is True
            while motor_running and running:
                if direction_forward:
                    GPIO.output(PUL, GPIO.LOW)
                    sleep(delay)
                    GPIO.output(PUL, GPIO.HIGH)
                    sleep(delay)
                else:
                    GPIO.output(PUL, GPIO.HIGH)
                    sleep(delay)
                    GPIO.output(PUL, GPIO.LOW)
                    sleep(delay)

            # Disable motor when stopped
            GPIO.output(ENA, GPIO.LOW)
        
        sleep(0.01)  # Small delay to prevent CPU hogging

def stop_program():
    """Clean up and exit the program"""
    global running
    running = False
    stop_motor()
    print("Cleaning up GPIO")
    GPIO.cleanup()
    print("Exiting program")

def print_instructions():
    """Print keyboard control instructions"""
    print("Keyboard controls:")
    print("- Press UP arrow key (↑) to move forward")
    print("- Press DOWN arrow key (↓) to move backward")
    print("- Press SPACE to stop the motor")
    print("- Press ESC or Q to exit")

def handle_keyboard_input():
    """Handle keyboard input in the main thread"""
    global running, motor_running, direction_forward
    
    try:
        while running:
            # Check if there's input available
            if select.select([sys.stdin], [], [], 0.05)[0]:
                key = readchar.readkey()
                
                if key == readchar.key.UP:
                    direction_forward = True
                    start_motor()
                    print("Up key pressed - Moving forward")
                elif key == readchar.key.DOWN:
                    direction_forward = False
                    start_motor()
                    print("Down key pressed - Moving backward")
                elif key in (readchar.key.ESC, 'q', 'Q'):
                    print("Exiting program")
                    stop_program()
                    break
                elif key == readchar.key.SPACE:
                    stop_motor()
                    print("Space pressed - Stopping motor")
            
            sleep(0.01)  # Small delay to prevent CPU hogging
    except Exception as e:
        print(f"Error in keyboard handling: {e}")
    finally:
        stop_program()

def main():
    """Main function to run the program"""
    setup_gpio()
    
    # Start the motor control thread
    motor_thread = threading.Thread(target=pulse_motor)
    motor_thread.daemon = True
    motor_thread.start()
    
    print_instructions()
    handle_keyboard_input()

if __name__ == "__main__":
    main()
