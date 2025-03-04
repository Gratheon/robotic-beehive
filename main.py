import Jetson.GPIO as GPIO
import readchar
import threading
from time import sleep

PUL = 33  # Stepper Drive Pulses
DIR = 40  # Controller Direction Bit (High for Controller default / LOW to Force a Direction Change).
ENA = 22  # Controller Enable Bit (High to Enable / LOW to Disable).

GPIO.setmode(GPIO.BOARD)  # Jetson Nano

GPIO.setup(PUL, GPIO.OUT)
GPIO.setup(DIR, GPIO.OUT)
GPIO.setup(ENA, GPIO.OUT)

print('Initialization Completed')

# Motor control parameters
base_delay = 0.0005  # Base delay between PUL pulses
up_speed_factor = 1.5  # Increase this factor to give more torque when moving up
print('Base speed set to ' + str(base_delay))

# Control flags
running = True
motor_running = False
direction_up = True


def pulse_motor():
    """Function to continuously pulse the motor while motor_running is True"""
    global motor_running, direction_up

    while running:
        if motor_running:
            # Set direction
            GPIO.output(DIR, GPIO.LOW if direction_up else GPIO.HIGH)
            print('Moving Up' if direction_up else 'Moving Down')

            # Enable motor
            GPIO.output(ENA, GPIO.HIGH)
            
            # Adjust delay based on direction
            current_delay = base_delay * (1 / up_speed_factor) if direction_up else base_delay

            # Pulse the motor as long as motor_running is True
            while motor_running and running:
                GPIO.output(PUL, GPIO.HIGH)
                sleep(current_delay)
                GPIO.output(PUL, GPIO.LOW)
                sleep(current_delay)

            # Disable motor when stopped
            GPIO.output(ENA, GPIO.LOW)

        sleep(0.01)  # Small delay to prevent CPU hogging


def stop_program():
    """Clean up and exit the program"""
    global running
    running = False
    global motor_running
    motor_running = False
    print("Cleaning up GPIO")
    GPIO.cleanup()
    print("Exiting program")


# Start the motor control thread
motor_thread = threading.Thread(target=pulse_motor)
motor_thread.daemon = True
motor_thread.start()

# Handle keyboard input in the main thread
print("Keyboard controls:")
print("- Press UP arrow key (↑) to move up")
print("- Press DOWN arrow key (↓) to move down")
print("- Press SPACE to stop the motor")
print("- Press ESC or Q to exit")

try:
    while running:
        key = readchar.readkey()

        if key == readchar.key.UP:
            direction_up = True
            motor_running = True
            print("Up key pressed - Moving up")
        elif key == readchar.key.DOWN:
            direction_up = False
            motor_running = True
            print("Down key pressed - Moving down")
        elif key in (readchar.key.ESC, 'q', 'Q'):
            print("Exiting program")
            stop_program()
            break
        elif key == readchar.key.SPACE:
            motor_running = False
            print("Space pressed - Stopping motor")
except Exception as e:
    print(f"Error in keyboard handling: {e}")
finally:
    stop_program()
