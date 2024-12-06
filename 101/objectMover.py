#!/usr/bin/env python3
#coding=utf-8
import time
from Arm_Lib import Arm_Device

# Initialize DOFBOT
Arm = Arm_Device()
time.sleep(0.1)

# Control the clamp (servo 6)
def arm_clamp_block(enable):
    if enable == 0:  # Release
        Arm.Arm_serial_servo_write(6, 60, 400)
    else:  # Clamp
        Arm.Arm_serial_servo_write(6, 130, 400)
    time.sleep(0.5)

# Move the arm to specified positions
def arm_move(p, s_time=500):
    for i in range(5):
        id = i + 1
        if id == 5:
            time.sleep(0.1)
            Arm.Arm_serial_servo_write(id, p[i], int(s_time * 1.2))
        elif id == 1:
            Arm.Arm_serial_servo_write(id, p[i], int(3 * s_time / 4))
        else:
            Arm.Arm_serial_servo_write(id, p[i], int(s_time))
        time.sleep(0.01)
    time.sleep(s_time / 1000)

# Positions for different actions
p_front = [90, 60, 50, 50, 90]  # Front position
p_right = [0, 60, 50, 50, 90]   # Right position
p_left = [180, 60, 50, 50, 90]  # Left position
p_top = [90, 80, 50, 50, 90]    # Top (transition) position
p_rest = [90, 130, 0, 0, 90]    # Rest position

def move_object(target):
    """
    Move an object from the front to the specified target side.
    
    Parameters:
    target (str): 'left' or 'right' indicating the movement direction.
    """
    if target not in ['left', 'right']:
        print("Invalid target! Use 'left' or 'right'.")
        return

    # Move to front position to pick object
    arm_clamp_block(0)  # Open clamp
    arm_move(p_front, 1000)  # Move to front position
    arm_clamp_block(1)  # Clamp object

    # Transition to top position
    arm_move(p_top, 1000)

    # Move to target position
    if target == 'left':
        arm_move(p_left, 1000)
    elif target == 'right':
        arm_move(p_right, 1000)

    # Release object
    arm_clamp_block(0)

    # Return to rest position
    arm_move(p_top, 1000)
    arm_move(p_rest, 1000)

# User input for selecting target side
while True:
    target = input("Enter target position ('left' or 'right', or 'exit' to quit): ").strip().lower()
    if target == 'exit':
        break
    move_object(target)

del Arm  # Release DOFBOT object
