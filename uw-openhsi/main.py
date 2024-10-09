import json
import subprocess
import os
import time
import signal
from multiprocessing import Process
from openhsi.cameras import IDSCamera



def timeout_handler(signum, frame):
    raise KeyboardInterrupt

def record_hsi(n_lines, cube_save_dir, json_path = 'configs/cam_settings_ids.json'):

    with IDSCamera(n_lines=n_lines, 
                    processing_lvl = -1,
                    json_path = json_path) as cam:
        cam.collect()
        cam.save(save_dir=cube_save_dir)


def record_svo(output_svo_file, command_record):
    print(f"######################### RECORDING SVO FILE {output_svo_file} #########################")
    try:
        # Execute func.py with subprocess.run
        # Ensures that recording stops either after prescribed duration or at keyboard interupt in terminal
        try:
            result = subprocess.run(command_record, capture_output=True, text=True)
        except KeyboardInterrupt:
            print("Timeout reached. Stopping the command.")

        # Process the output if needed (optional)
        if result.returncode == 0:
            print("Recording execution successful!")
            print(result.stdout)  # Access standard output (optional)
        else:
            print("Recording execution failed.")
            print(result.stderr)  # Access standard error (optional)

    except (subprocess.CalledProcessError, NameError) as e:
        print("Error occurred while calling record_svo.py:", e)
    

if __name__ == '__main__':

    # Tweakable parameters:
    record_time_zed = 20 # This is how long the recording lasts for

    fps_hsi = 135


    ## Alter the settings
    with open('configs/cam_settings_ids.json', 'r') as f:
        data = json.load(f)


    data['pixel_format'] = 'Mono8' # The fastest data to record is Mono8 (Up to 160 FPS)
    data['exposure_ms'] = 1e3/fps_hsi
    #data['exposure_ms'] = 1e3/(2*81.953778)

    row_start = 333
    row_width = 550

    #row_start = 0
    #row_width = 1216

    data['win_offset'] = [0, row_start]
    data['win_resolution'] = [1936, row_width]

    data['resolution'][0] = 552


    with open('configs/cam_settings_ids.json', 'w') as f:
        json.dump(data, f, indent=4)

    n_lines = 500


    fps_stereo = 5


    # Register the timeout handler which causes an alarm to go off
    #signal.signal(signal.SIGALRM, timeout_handler)
    #signal.alarm(record_time) 



    # Path to func.py

    print(os.getcwd())
    func_path_record = "/home/ubuntu/VSCodeProjects/uw-openhsi/uw-openhsi/zed/record_svo.py"  # Adjust the path to your func.py
    func_path_pose_post = "/home/ubuntu/VSCodeProjects/uw-openhsi/uw-openhsi/zed/position_post.py"
    func_path_export = "/home/ubuntu/VSCodeProjects/uw-openhsi/uw-openhsi/zed/export_svo_images_or_vid.py" 
    func_mesh_post = "/home/ubuntu/VSCodeProjects/uw-openhsi/uw-openhsi/zed/mesh_post.py" 


    # The time the script starts
    time_start = time.time()

    time_stop_zed = time_start + record_time_zed


    print(time_stop_zed)
    current_time_utc = time.gmtime()
    current_time_utc_str = time.strftime("%Y-%m-%d_%H-%M-%S", current_time_utc)



    # Define arguments for my_function (if needed)

    capture_path = os.path.join("captured_data", f"{current_time_utc_str}")
    capture_path = os.path.join("captured_data", 'black_white_lines')

    if not os.path.exists(capture_path):
        os.mkdir(capture_path)



    output_svo_file = os.path.join(capture_path, "recording.svo2")
    output_pose_file = os.path.join(capture_path, "pose.csv")
    output_path_dir = os.path.join(capture_path, "png_dir")
    if not os.path.exists(output_path_dir):
        os.mkdir(output_path_dir)


    output_dir_hsi = os.path.join(capture_path, "hsi_dir")
    if not os.path.exists(output_dir_hsi):
        os.mkdir(output_dir_hsi)

    output_mesh_file = os.path.join(capture_path,  "mesh_file.obj")



    function_arguments = [output_svo_file]  # Adjust arguments as needed


    # Construct the command with the required argument
    command_record = ["python", func_path_record, "--output_svo_file", output_svo_file, "--fps", str(fps_stereo), "--time_stop_zed", str(time_stop_zed)]

    # Construct the command with the required argument
    command_export = ["python", func_path_export, "--input_svo_file", output_svo_file, "--output_path_dir", output_path_dir]

    # Construct the command with the required argument
    command_pose_post = ["python", func_path_pose_post, "--input_svo_file", output_svo_file, "--output_pose_file", output_pose_file]

    # Construct the command with the required argument
    command_mesh_post = ["python", func_mesh_post, "--input_svo_file", output_svo_file, "--output_mesh_file", output_mesh_file]

    # Which products to estimate
    process_dict = {'record': True,
                    'record_svo': False,
                    'record_hsi': True,
                    'pose_post': False,
                    'export': False,
                    'mesh_post': False}


    ## Real time
    if process_dict["record"]:
        if process_dict["record_hsi"]:
            """p1 = Process(target=record_hsi, kwargs = {"n_lines":n_lines, 'cube_save_dir':output_dir_hsi})

            p1.start()

            
            p1.join()"""
            record_hsi(n_lines, output_dir_hsi)

        if process_dict["record_svo"]:
            p2 = Process(target=record_svo, kwargs = {"output_svo_file":output_svo_file, 'command_record':command_record})

            p2.start()

            # Wait for processes to finish (optional)
            p2.join()



    if process_dict["export"]:
        try:
            # Execute func.py with subprocess.run
            result = subprocess.run(command_export, capture_output=True, text=True)

            # Process the output if needed (optional)
            if result.returncode == 0:
                print("Pose estimation execution successful!")
                print(result.stdout)  # Access standard output (optional)
            else:
                print("Pose estimateion execution failed.")
                print(result.stderr)  # Access standard error (optional)

        except subprocess.CalledProcessError as e:
            print("Error occurred while calling position_post.py", e)

    if process_dict["pose_post"]:
        print(f"######################### Pose estimation from SVO FILE {output_svo_file} #########################")
        try:
            # Execute func.py with subprocess.run
            result = subprocess.run(command_pose_post, capture_output=True, text=True)

            # Process the output if needed (optional)
            if result.returncode == 0:
                print("Pose estimation execution successful!")
                print(result.stdout)  # Access standard output (optional)
            else:
                print("Pose estimateion execution failed.")
                print(result.stderr)  # Access standard error (optional)

        except subprocess.CalledProcessError as e:
            print("Error occurred while calling position_post.py", e)





    if process_dict["mesh_post"]:
        try:
            # Execute func.py with subprocess.run
            result = subprocess.run(command_mesh_post, capture_output=True, text=True)

            # Process the output if needed (optional)
            if result.returncode == 0:
                print("Mesh estimation execution successful!")
                print(result.stdout)  # Access standard output (optional)
            else:
                print("Mesh estimation execution failed.")
                print(result.stderr)  # Access standard error (optional)

        except subprocess.CalledProcessError as e:
            print("Error occurred while calling position_post.py", e)
        
    
    if process_dict["mesh_post"]:
        try:
            # Execute func.py with subprocess.run
            result = subprocess.run(command_mesh_post, capture_output=True, text=True)

            # Process the output if needed (optional)
            if result.returncode == 0:
                print("Mesh estimation execution successful!")
                print(result.stdout)  # Access standard output (optional)
            else:
                print("Mesh estimation execution failed.")
                print(result.stderr)  # Access standard error (optional)

        except subprocess.CalledProcessError as e:
            print("Error occurred while calling position_post.py", e)


