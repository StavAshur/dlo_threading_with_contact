#!/usr/bin/env python3
import rospy
import moveit_commander
from geometry_msgs.msg import PoseStamped
import sys

def main():
    moveit_commander.roscpp_initialize(sys.argv)
    rospy.init_node('add_walls_node', anonymous=True)
    
    scene = moveit_commander.PlanningSceneInterface()
    
    # MoveIt needs a second to connect the scene to the ROS master
    rospy.sleep(2.0) 

    def add_box(name, x, y, z, size_x, size_y, size_z):
        box_pose = PoseStamped()
        box_pose.header.frame_id = "base_link"
        box_pose.pose.position.x = x
        box_pose.pose.position.y = y
        box_pose.pose.position.z = z
        box_pose.pose.orientation.w = 1.0
        scene.add_box(name, box_pose, size=(size_x, size_y, size_z))

    rospy.loginfo("Adding 3 collision walls to the planning scene...")
    
    # 1. Back Wall (Behind the robot)
    add_box("back_wall", -0.6, 0.0, 0.5, 0.1, 2.0, 2.0)
    # 2. Left Wall
    add_box("left_wall", 0.0, 0.9, 0.5, 2.0, 0.1, 2.0)
    # 3. Right Wall
    add_box("right_wall", 0.0, -0.9, 0.5, 2.0, 0.1, 2.0)

    rospy.sleep(1.0) # Ensure messages finish publishing before the node dies

if __name__ == '__main__':
    try:
        main()
    except rospy.ROSInterruptException:
        pass