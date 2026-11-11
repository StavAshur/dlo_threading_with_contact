#!/usr/bin/env python3
import rospy
import moveit_commander
import random
import math
import sys
import tf.transformations
from geometry_msgs.msg import Pose
import copy

def main():
    # Initialize commander and node
    moveit_commander.roscpp_initialize(sys.argv)
    rospy.init_node('random_mover_node', anonymous=True)

    # 1. CRITICAL: Wait for MoveGroup to be fully initialized
    rospy.loginfo("Waiting for MoveGroup to finish booting...")
    rospy.sleep(8.0)  # Increase this if demo.launch is slow on your ThinkCentre

    # 2. Initialize the robot and scene
    robot = moveit_commander.RobotCommander()
    scene = moveit_commander.PlanningSceneInterface()
    
    # group_name = "arm_left"
    
    # Try-Except block to catch the initialization error
    try:
        move_group_left = moveit_commander.MoveGroupCommander("arm_left")
        move_group_right = moveit_commander.MoveGroupCommander("arm_right")
    except Exception as e:
        rospy.logerr(f"Could not connect to planning group 'arm_left': {e}")
        return

    move_group_left.set_max_velocity_scaling_factor(0.05)
    move_group_left.set_max_acceleration_scaling_factor(0.05)

    # Fetch duration
    duration_sec = rospy.get_param('~duration', 30.0)

    # Ball limits
    CENTER_X, CENTER_Y, CENTER_Z = 0.6, 0.0, 1.2
    RADIUS = 0.4

    rospy.loginfo("Moving to initial 'start' state...")
    move_group_left.set_named_target("start")
    move_group_left.go(wait=True)
    move_group_left.stop()
    move_group_left.clear_pose_targets()
    move_group_left.set_max_velocity_scaling_factor(0.05)
    move_group_left.set_max_acceleration_scaling_factor(0.05)
    start_time = rospy.Time.now()
    rospy.loginfo(f"Starting linear random movements for {duration_sec} seconds.")

    while not rospy.is_shutdown() and (rospy.Time.now() - start_time).to_sec() < duration_sec:
        # Rejection sampling for the ball
        while True:
            dx = random.uniform(-RADIUS, RADIUS)
            dy = random.uniform(-RADIUS, RADIUS)
            dz = random.uniform(-RADIUS, RADIUS)
            if (dx**2 + dy**2 + dz**2) <= RADIUS**2:
                break
        target_pose = Pose()

        target_x = CENTER_X + dx
        target_y = CENTER_Y + dy
        target_z = CENTER_Z + dz

        target_pose.position.x = target_x
        target_pose.position.y = target_y
        target_pose.position.z = target_z

        right_arm_pose = move_group_right.get_current_pose().pose
        right_arm_x = right_arm_pose.position.x
        right_arm_z = right_arm_pose.position.z

        while True:
            q = tf.transformations.random_quaternion()
            R = tf.transformations.quaternion_matrix(q)
            
            # The Z-axis of the end-effector is represented by the 3rd column of R:
            # R[0, 2] = X-component w.r.t base_link
            # R[1, 2] = Y-component w.r.t base_link
            # R[2, 2] = Z-component w.r.t base_link

            # Condition 1: Y-axis points towards the right arm (negative Y-component)
            points_right = (R[1, 2] < 0)
            
            # Condition 2: Z-axis points down if above the right arm, up if below
            if target_z > right_arm_z:
                correct_z_dir = (R[2, 2] < 0) # Pointing down
            else:
                correct_z_dir = (R[2, 2] > 0) # Pointing up
                
            # Condition 3: Z-axis points in positive X if behind right arm, negative X if in front
            if target_x < right_arm_x:
                correct_x_dir = (R[0, 2] > 0) # Pointing in positive X
            else:
                correct_x_dir = (R[0, 2] < 0) # Pointing in negative X
                
            # If all three directional conditions are met, accept this orientation!
            if points_right and correct_z_dir and correct_x_dir:
                break
                
        target_pose.orientation.x = q[0]
        target_pose.orientation.y = q[1]
        target_pose.orientation.z = q[2]
        target_pose.orientation.w = q[3]
        target_pose.orientation.x, target_pose.orientation.y = q[0], q[1]
        target_pose.orientation.z, target_pose.orientation.w = q[2], q[3]

        # 3. Cartesian Path Planning (Linear Motion)
        waypoints = [move_group_left.get_current_pose().pose, target_pose]
        (plan, fraction) = move_group_left.compute_cartesian_path(waypoints, 0.01, True)

        if fraction > 0.9: # Accept if at least 90% of the path is linear
            rospy.loginfo(f"Executing linear path (coverage: {fraction*100}%)")
            move_group_left.execute(plan, wait=True)

            rospy.sleep(0.5) # Brief pause at the target
            
            rospy.loginfo("Reversing trajectory to return linearly to start...")
            reverse_plan = copy.deepcopy(plan)
            
            # Get the total duration of the forward plan
            total_time = plan.joint_trajectory.points[-1].time_from_start
            
            reversed_points = []
            # Loop through the points backward
            for pt in reversed(plan.joint_trajectory.points):
                new_pt = copy.deepcopy(pt)
                
                # Invert the timestamps
                new_pt.time_from_start = total_time - pt.time_from_start
                
                # Invert velocities and accelerations for smooth backward motion
                if new_pt.velocities:
                    new_pt.velocities = [-v for v in pt.velocities]
                if new_pt.accelerations:
                    new_pt.accelerations = [-a for a in pt.accelerations]
                    
                reversed_points.append(new_pt)
                
            # Replace the forward points with our new reversed points
            reverse_plan.joint_trajectory.points = reversed_points
            
            rospy.loginfo("Executing reverse linear path...")
            move_group_left.execute(reverse_plan, wait=True)
        else:
            rospy.logwarn(f"Linear path failed (only {fraction*100}% reachable). Retrying...")

        rospy.sleep(0.5)

if __name__ == '__main__':
    main()