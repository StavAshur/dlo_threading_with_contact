- Switch to anagement mode SYSTEM INFO (main menu) -> SECURITY, password is 99999999

- When an error pops in the pendant use CANCEL key (top right of the pendant next to SELECT) to continue

- robot IP address can be found in the pendant SYSTEM INFO (main menu) -> NETWORK SERVICE (We found 192.168.255.3)

- Used these terminal commands to set up the connection (may need variations depending on the ethernet setup):
    sudo ip addr add 192.168.255.100/24 dev enp2s0-  sudo ip link set enp2s0 up 

- To connect to the robot directly via ethernet set up the network connection in the Ubuntu network settings (top right next to power and audio).
    Make the connection manual, address 192.168.255.X where X should be 1-10 and not the same as the robot's, mask 255.255.255.0

- A simple demo silmulation (RViz + MoveIt) can be started using the command:
    roslaunch motoman_sda10f_moveit_config demo.launch

- Visualizing the actual robot can be done using the terminal command:
    roslaunch motoman_sda10f_support robot_state_visualize_sda10f.launch robot_ip:=192.168.255.3 controller:=fs100

- Getting information about the robot's current position: ROBOT (main menue) -> CURRENT POSITION

- Changing the numbers to degrees is done using the DISPLAY button (top menu)

- Speed is set in SETUP (main menu 2nd page) -> SET SPEED. Default seems to be 0.78, 1.56, 3.12, 6.25, 12.5, 25, 50, 100 (lowest speed is for joint 1, highest for 8). Can only be done in management mode.

- Getting a full RViz + MoveIt setup is done using the command:
    roslaunch motoman_sda10f_moveit_config moveit_planning_execution.launch robot_ip:=192.168.255.3 controller:=fs100

- Safety walls can be added using a node with the command:
    rosrun yaron_plan_to_gaol add_walls.py

- The robot must be enabled before it moves by using the command 
    rosservice call /robot_enable
    
    This can be turned off using the command 
    rosservice call /robot_disable



================== Bota sensor ==========================


- Had to install a driver which I got here https://wiki.ros.org/bota_driver with the command:
    sudo apt install ros-noetic-bota-driver

- Another good source is https://gitlab.com/botasys/legacy/bota_driver/-/blob/master/README.md where I found the command 
    sudo apt install ros-<DISTRO>-ethercat-grant libxmlrpcpp-dev librosconsole-dev
    Also it says there to add to /etc/security/limits.conf the following lines:
    <username>		 soft	 rtprio	  99
    <username>		 hard	 rtprio	  99

- The command to verify the sensor is operational is:
    sudo /opt/ros/noetic/bin/slaveinfo enp2s0
    apparently you cannot ping a sensor

- For some reason I had a problem with the system path so had to do:
    sudo sh -c "echo '/opt/ros/noetic/lib' > /etc/ld.so.conf.d/ros-noetic.conf

- the command to run something is:
    roslaunch rokubimini_ethercat rokubimini_ethercat.launch ethercat_bus:=enp2s0
    where the last bit is because of my specific network settings, this is the port I'm using.

- resseting the F/T forces (tare) is done with the command:
    rosservice call /bus0/ft_sensor0/reset_wrench "{desired_wrench: {force:  {x: 0.0, y: 0.0, z: 0.0}, torque: {x: 0.0, y: 0.0, z: 0.0}}}"

- Getting the reading is done with the command:
    rostopic echo /bus0/ft_sensor0/ft_sensor_readings/wrench



================== Zed camera ==========================

- In order to use the camera need to install SDK

- The Zed repository zed-ros-wrapper can be found in:
    https://github.com/stereolabs/zed-ros-wrapper

- Activating the depth viewer (for testing) can be done using the command:
    /usr/local/zed/tools/ZED_Depth_Viewer