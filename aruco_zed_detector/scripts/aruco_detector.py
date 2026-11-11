#!/usr/bin/env python3

import rospy
import cv2
import numpy as np
from sensor_msgs.msg import Image, CameraInfo
from geometry_msgs.msg import TransformStamped, PointStamped
from cv_bridge import CvBridge, CvBridgeError
import tf2_ros
import tf.transformations as tf_trans

class ArucoDetector:
    def __init__(self):
        rospy.init_node('aruco_detector_node', anonymous=True)
        
        self.bridge = CvBridge()
        
        self.camera_matrix = None
        self.dist_coeffs = None
        
        # Measured marker length in meters
        self.marker_length = rospy.get_param("~marker_length", 0.19) 
        self.cluster_t = rospy.get_param("~cluster_distance", 20)
        
        # --- State Machine Variables ---
        self.state = "CALIBRATING"
        self.calibration_start_time = None
        self.rvecs_list = []
        self.tvecs_list = []
        self.avg_rvec = None
        self.avg_tvec = None
        
        # OpenCV 4.7+ ArUco API
        self.aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_6X6_250)
        self.aruco_params = cv2.aruco.DetectorParameters()
        self.aruco_detector = cv2.aruco.ArucoDetector(self.aruco_dict, self.aruco_params)
        
        half_l = self.marker_length / 2.0
        self.obj_points = np.array([
            [-half_l,  half_l, 0],
            [ half_l,  half_l, 0],
            [ half_l, -half_l, 0],
            [-half_l, -half_l, 0]
        ], dtype=np.float32)
        
        self.tf_broadcaster = tf2_ros.TransformBroadcaster()
        self.centroid_pub = rospy.Publisher("/red_centroids", PointStamped, queue_size=10)

        image_topic = "/zed2/zed_node/left/image_rect_color"
        info_topic = "/zed2/zed_node/left/camera_info"
        
        rospy.Subscriber(info_topic, CameraInfo, self.camera_info_cb)
        rospy.Subscriber(image_topic, Image, self.image_cb, queue_size=1)
        
        rospy.loginfo("Node Initialized. Waiting to see Marker 42 to begin calibration...")

    def camera_info_cb(self, msg):
        if self.camera_matrix is None:
            self.camera_matrix = np.array(msg.K).reshape((3, 3))
            self.dist_coeffs = np.array(msg.D)
            self.camera_frame_id = msg.header.frame_id
            self.inv_K = np.linalg.inv(self.camera_matrix)
            rospy.loginfo("Camera Info received.")

    def image_cb(self, msg):
        if self.camera_matrix is None:
            return

        try:
            cv_image = self.bridge.imgmsg_to_cv2(msg, "bgr8")
        except CvBridgeError as e:
            rospy.logerr(f"CV Bridge Error: {e}")
            return

        # ==========================================
        # STATE 1: CALIBRATING ARUCO POSE (3 SECONDS)
        # ==========================================
        if self.state == "CALIBRATING":
            corners, ids, rejected = self.aruco_detector.detectMarkers(cv_image)

            if ids is not None:
                cv2.aruco.drawDetectedMarkers(cv_image, corners, ids)
                
                for i in range(len(ids)):
                    if ids[i][0] == 42:
                        corner = corners[i][0]
                        success, rvec, tvec = cv2.solvePnP(
                            self.obj_points, corner, self.camera_matrix, self.dist_coeffs, flags=cv2.SOLVEPNP_IPPE_SQUARE
                        )
                        
                        if success:
                            # Start the timer on the FIRST successful detection
                            if self.calibration_start_time is None:
                                self.calibration_start_time = rospy.Time.now()
                                rospy.loginfo("Marker 42 found! Keep it still. Calibrating for 3 seconds...")
                            
                            # Store the vectors for averaging
                            self.rvecs_list.append(rvec)
                            self.tvecs_list.append(tvec)
                            # cv2.drawFrameAxes(cv_image, self.camera_matrix, self.dist_coeffs, rvec, tvec, 0.05)

            # Check if 3 seconds have passed since the first detection
            if self.calibration_start_time is not None:
                elapsed_time = (rospy.Time.now() - self.calibration_start_time).to_sec()
                
                if elapsed_time >= 3.0:
                    if len(self.rvecs_list) > 0:
                        # Average the vectors
                        self.avg_rvec = np.mean(self.rvecs_list, axis=0)
                        self.avg_tvec = np.mean(self.tvecs_list, axis=0)
                        
                        self.state = "TRACKING"
                        rospy.loginfo(f"Calibration Complete! Averaged {len(self.rvecs_list)} frames.")
                        rospy.loginfo("ArUco detection disabled. Now tracking red clusters exclusively.")
                    else:
                        # Fallback just in case it lost the marker immediately after finding it
                        self.calibration_start_time = None
                        rospy.logwarn("Calibration failed: Lost marker. Restarting calibration...")

        # ==========================================
        # STATE 2: TRACKING RED CLUSTERS
        # ==========================================
        elif self.state == "TRACKING":
            # 1. Constantly publish the locked-in TF frame using the current timestamp
            self.publish_tf(msg.header.stamp, 42, self.avg_rvec, self.avg_tvec)

            # 2. Process red clusters using the locked-in pose
            self.process_red_clusters(cv_image, self.avg_rvec, self.avg_tvec, msg.header.stamp, 42)

            # Draw the static axes on the image so you know exactly where the virtual plane is
            cv2.drawFrameAxes(cv_image, self.camera_matrix, self.dist_coeffs, self.avg_rvec, self.avg_tvec, 0.05)
            
            

        # Show the main image window
        cv2.imshow("Detection & Tracking Window", cv_image)
        cv2.waitKey(1)

    def process_red_clusters(self, cv_image, rvec, tvec, stamp, marker_id):
        hsv = cv2.cvtColor(cv_image, cv2.COLOR_BGR2HSV)
        
        lower_red1 = np.array([0, 100, 100])
        upper_red1 = np.array([10, 255, 255])
        mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
        
        lower_red2 = np.array([170, 100, 100])
        upper_red2 = np.array([180, 255, 255])
        mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
        
        red_mask = mask1 | mask2

        # Optional: Show debug mask to tune thresholds (you can comment this out once it's perfect)
        # cv2.imshow("DEBUG: Red Pixel Mask", red_mask)

        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (self.cluster_t, self.cluster_t))
        closed_mask = cv2.morphologyEx(red_mask, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(closed_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        rmat, _ = cv2.Rodrigues(rvec)
        tvec_3x1 = tvec.reshape(3, 1)
        plane_normal = rmat[:, 2].reshape(3, 1)
        

        # rospy.loginfo("found " + str(len(contours)) + " red clusters")



        for i, cnt in enumerate(contours):
            M = cv2.moments(cnt)
            if M["m00"] == 0:
                continue
            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])

            cv2.circle(cv_image, (cx, cy), 6, (0, 255, 0), -1)
            cv2.putText(cv_image, f"R{i}", (cx + 8, cy - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

            ray_c = self.inv_K.dot(np.array([[cx], [cy], [1.0]]))
            
            numerator = np.dot(plane_normal.T, tvec_3x1)
            denominator = np.dot(plane_normal.T, ray_c)
            
            if np.abs(denominator) < 1e-6:
                continue 
                
            s = numerator / denominator
            P_c = s * ray_c
            P_m = np.dot(rmat.T, (P_c - tvec_3x1))
            
            pt_msg = PointStamped()
            pt_msg.header.stamp = stamp
            pt_msg.header.frame_id = f"aruco_marker_{marker_id}"
            
            pt_msg.point.x = float(P_m[0][0])
            pt_msg.point.y = float(P_m[1][0])
            pt_msg.point.z = 0.0 
            
            self.centroid_pub.publish(pt_msg)

    def publish_tf(self, stamp, marker_id, rvec, tvec):
        t = TransformStamped()
        
        t.header.stamp = stamp
        t.header.frame_id = self.camera_frame_id
        t.child_frame_id = f"aruco_marker_{marker_id}"
        
        t.transform.translation.x = float(tvec[0][0])
        t.transform.translation.y = float(tvec[1][0])
        t.transform.translation.z = float(tvec[2][0])
        
        rmat, _ = cv2.Rodrigues(rvec)
        transform_matrix = np.eye(4)
        transform_matrix[:3, :3] = rmat
        quat = tf_trans.quaternion_from_matrix(transform_matrix)
        
        t.transform.rotation.x = float(quat[0])
        t.transform.rotation.y = float(quat[1])
        t.transform.rotation.z = float(quat[2])
        t.transform.rotation.w = float(quat[3])
        
        self.tf_broadcaster.sendTransform(t)

if __name__ == '__main__':
    try:
        detector = ArucoDetector()
        rospy.spin()
    except rospy.ROSInterruptException:
        pass
    finally:
        cv2.destroyAllWindows()