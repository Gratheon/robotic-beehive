from gpiozero import AngularServo
#import RPi.GPIO as GPIO
import time

#GPIO.setmode(GPIO.BCM)

#servo_pin = 17
#GPIO.setup(servo_pin, GPIO.OUT)

servo = AngularServo(17, min_pulse_width=0.0006, max_pulse_width=0.0023)

#pwm = GPIO.PWM(servo_pin, 50)
#pwm.start(2.5)

try:
    while True:
        servo.angle = 90
        time.sleep(2)
        
chrome+        servo.angle = 0
        time.sleep(2)
        #pwm.ChangeDutyCycle(2.5)
        #time.sleep(1)
        
        #pwm.ChangeDutyCycle(7.5);
        #time.sleep(1)
except KeyboardInterrupt:
    pass

#finally:
#    pwm.stop()
#    GPIO.cleanup()
