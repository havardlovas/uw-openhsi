


########################################################################
#
# Copyright (c) 2022, STEREOLABS.
#
# All rights reserved.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
########################################################################








import argparse
import pandas as pd
import pyzed.sl as sl



def parse_args(init):
    if len(opt.input_svo_file) > 0 and (opt.input_svo_file.endswith(".svo") or opt.input_svo_file.endswith(".svo2")):
        init.set_from_svo_file(opt.input_svo_file)
        print("[Sample] Using SVO File input: {0}".format(opt.input_svo_file))
    elif len(opt.ip_address) > 0 :
        ip_str = opt.ip_address
        if ip_str.replace(':','').replace('.','').isdigit() and len(ip_str.split('.'))==4 and len(ip_str.split(':'))==2:
            init.set_from_stream(ip_str.split(':')[0],int(ip_str.split(':')[1]))
            print("[Sample] Using Stream input, IP : ",ip_str)
        elif ip_str.replace(':','').replace('.','').isdigit() and len(ip_str.split('.'))==4:
            init.set_from_stream(ip_str)
            print("[Sample] Using Stream input, IP : ",ip_str)
        else :
            print("Unvalid IP format. Using live stream")
    if ("resolution" in opt.resolution):
        init.camera_resolution = sl.RESOLUTION.HD2K
        print("[Sample] Using Camera in resolution HD2K")
    elif ("HD1200" in opt.resolution):
        init.camera_resolution = sl.RESOLUTION.HD1200
        print("[Sample] Using Camera in resolution HD1200")
    elif ("HD1080" in opt.resolution):
        init.camera_resolution = sl.RESOLUTION.HD1080
        print("[Sample] Using Camera in resolution HD1080")
    elif ("HD720" in opt.resolution):
        init.camera_resolution = sl.RESOLUTION.HD720
        print("[Sample] Using Camera in resolution HD720")
    elif ("SVGA" in opt.resolution):
        init.camera_resolution = sl.RESOLUTION.SVGA
        print("[Sample] Using Camera in resolution SVGA")
    elif ("VGA" in opt.resolution):
        init.camera_resolution = sl.RESOLUTION.VGA
        print("[Sample] Using Camera in resolution VGA")
    elif len(opt.resolution)>0: 
        print("[Sample] No valid resolution entered. Using default")
    else : 
        print("[Sample] Using default resolution")
        

def main():
    # Create a Camera object from old files
    init_params = sl.InitParameters(camera_resolution=sl.RESOLUTION.HD1080,
                                 coordinate_units=sl.UNIT.METER,
                                 coordinate_system=sl.COORDINATE_SYSTEM.RIGHT_HANDED_Z_UP)
    parse_args(init_params)

    
    zed = sl.Camera()
    status = zed.open(init_params)
    if status != sl.ERROR_CODE.SUCCESS:
        print("Camera Open", status, "Exit program.")
        exit(1)


    # Enable positional tracking with default parameters
    py_transform = sl.Transform()  # First create a Transform object for TrackingParameters object
    tracking_parameters = sl.PositionalTrackingParameters(_init_pos=py_transform)
    err = zed.enable_positional_tracking(tracking_parameters)
    if err != sl.ERROR_CODE.SUCCESS:
        print("Enable positional tracking : "+repr(err)+". Exit program.")
        zed.close()
        exit()

    # Track the camera position during 1000 frames
    i = 0
    zed_pose = sl.Pose()

    zed_sensors = sl.SensorsData()
    runtime_parameters = sl.RuntimeParameters()
    
    can_compute_imu = zed.get_camera_information().camera_model != sl.MODEL.ZED
    # Create an empty DataFrame
    df = pd.DataFrame(columns=["Timestamp", "Tx", "Ty", "Tz", "Qx", "Qy", "Qz", "Qw"], dtype=object)

    nb_frames = zed.get_svo_number_of_frames()

    print(nb_frames)
    while i < nb_frames:
        if zed.grab(runtime_parameters) == sl.ERROR_CODE.SUCCESS:
            # Get the pose of the left eye of the camera with reference to the world frame
            zed.get_position(zed_pose, sl.REFERENCE_FRAME.WORLD)
            

            # Display the translation and timestamp
            py_translation = sl.Translation()
            tx = round(zed_pose.get_translation(py_translation).get()[0], 3)
            ty = round(zed_pose.get_translation(py_translation).get()[1], 3)
            tz = round(zed_pose.get_translation(py_translation).get()[2], 3)
            t_milli = zed_pose.timestamp.get_milliseconds()
            #print("Translation: Tx: {0}, Ty: {1}, Tz {2}, Timestamp: {3}\n".format(tx, ty, tz, t_milli))

            # Display the orientation quaternion
            py_orientation = sl.Orientation()
            qx = round(zed_pose.get_orientation(py_orientation).get()[0], 3)
            qy = round(zed_pose.get_orientation(py_orientation).get()[1], 3)
            qz = round(zed_pose.get_orientation(py_orientation).get()[2], 3)
            qw = round(zed_pose.get_orientation(py_orientation).get()[3], 3)
            #print("Orientation: Qx: {0}, Qy: {1}, Qz {2}, Qw: {3}\n".format(qx, qy, qz, qw))
            

            new_data = pd.Series({
                "Timestamp": zed_pose.timestamp.get_milliseconds(),
                "Tx": tx,
                "Ty": ty,
                "Tz": tz,
                "Qx": qx,  # Assuming orientation is also float
                "Qy": qy,
                "Qz": qz,
                "Qw": qw,
            })

            df = pd.concat([df, new_data.to_frame().T], ignore_index=True)  # Append as row

            if can_compute_imu:
                zed.get_sensors_data(zed_sensors, sl.TIME_REFERENCE.IMAGE)
                zed_imu = zed_sensors.get_imu_data()
                #Display the IMU acceleratoin
                acceleration = [0,0,0]
                zed_imu.get_linear_acceleration(acceleration)
                ax = round(acceleration[0], 3)
                ay = round(acceleration[1], 3)
                az = round(acceleration[2], 3)
                #print("IMU Acceleration: Ax: {0}, Ay: {1}, Az {2}\n".format(ax, ay, az))
                
                #Display the IMU angular velocity
                a_velocity = [0,0,0]
                zed_imu.get_angular_velocity(a_velocity)
                vx = round(a_velocity[0], 3)
                vy = round(a_velocity[1], 3)
                vz = round(a_velocity[2], 3)
                #print("IMU Angular Velocity: Vx: {0}, Vy: {1}, Vz {2}\n".format(vx, vy, vz))

                # Display the IMU orientation quaternion
                zed_imu_pose = sl.Transform()
                ox = round(zed_imu.get_pose(zed_imu_pose).get_orientation().get()[0], 3)
                oy = round(zed_imu.get_pose(zed_imu_pose).get_orientation().get()[1], 3)
                oz = round(zed_imu.get_pose(zed_imu_pose).get_orientation().get()[2], 3)
                ow = round(zed_imu.get_pose(zed_imu_pose).get_orientation().get()[3], 3)
                #print("IMU Orientation: Ox: {0}, Oy: {1}, Oz {2}, Ow: {3}\n".format(ox, oy, oz, ow))

            i = i + 1
    df.to_csv(opt.output_pose_file)
    # Close the camera
    zed.close()

if __name__ == "__main__":
    ## Reads a prerecorded svo and returns timestamped poses per image.
    parser = argparse.ArgumentParser()
    parser.add_argument('--input_svo_file', type=str, help='Path to an .svo file, if you want to replay it',default = 'test_svo.svo2')
    parser.add_argument('--output_pose_file', type=str, help='Path to pose csv',default = 'pose.csv')
    parser.add_argument('--ip_address', type=str, help='IP Adress, in format a.b.c.d:port or a.b.c.d, if you have a streaming setup', default = '')
    parser.add_argument('--resolution', type=str, help='Resolution, can be either HD2K, HD1200, HD1080, HD720, SVGA or VGA', default = 'HD1200')
    parser.add_argument('--roi_mask_file', type=str, help='Path to a Region of Interest mask file', default = '')
    opt = parser.parse_args()
    if (len(opt.input_svo_file)>0 and len(opt.ip_address)>0):
        print("Specify only input_svo_file or ip_address, or none to use wired camera, not both. Exit program")
        exit()
    main() 
