"""
@file    reconnect_callbacks.py
@author  IDS Imaging Development Systems GmbH
@date    2023-11-08

@brief   This application demonstrates how to register device connection change callbacks and handle a reconnected device

@version 1.0.1

Copyright (C) 2023 - 2024, IDS Imaging Development Systems GmbH.

The information in this document is subject to change without notice
and should not be construed as a commitment by IDS Imaging Development Systems GmbH.
IDS Imaging Development Systems GmbH does not assume any responsibility for any errors
that may appear in this document.

This document, or source code, is provided solely as an example of how to utilize
IDS Imaging Development Systems GmbH software libraries in a sample application.
IDS Imaging Development Systems GmbH does not assume any responsibility
for the use or reliability of any portion of this document.

General permission to copy or modify is hereby granted.
"""
from ids_peak import ids_peak

from typing import Optional


class IDSCam:
    def __init__(self):
        # Initialize library, has to be matched by a Library.Close() call
        ids_peak.Library.Initialize()

        self.device_manager: ids_peak.DeviceManager = ids_peak.DeviceManager.Instance()
        self.acquisition_running: bool = False
        self.device: Optional[ids_peak.Device] = None
        self.remote_nodemap: Optional[ids_peak.NodeMap] = None
        self.data_stream: Optional[ids_peak.DataStream] = None

        self.register_callbacks()

    @staticmethod
    def device_found(device: ids_peak.DeviceDescriptor):
        """
        The 'found' event is triggered if a new device is found upon calling
        `DeviceManager.Update()`
        """
        print(f"Found-Device-Callback: Key={device.Key()}")

    @staticmethod
    def device_lost(key: str):
        """
        The 'lost' event is only called for this application's opened devices if
        a device is closed explicitly or if connection is lost while the reconnect is disabled,
        otherwise the 'disconnected' event is triggered.
        Other devices that were not opened or were opened by someone else still trigger
        a 'lost' event.
        """
        print(f"Lost-Device-Callback: Key={key}")

    def ensure_compatible_buffers_and_restart_acquisition(
            self,
            reconnect_information: ids_peak.DeviceReconnectInformation
    ):
        """
        After a reconnect the PayloadSize might have changed, e.g. due to
        a reboot and the last parameter state not being saved in the
        starting UserSet. Here we check the PayloadSize and
        reallocate the buffers if we encounter a mismatch.

        We also start the local and remote acquistion if necessary.
        """
        payload_size = self.remote_nodemap.FindNode("PayloadSize").Value()

        has_payload_size_mismatch = payload_size != self.data_stream.AnnouncedBuffers()[
            0].Size()

        # The payload size might have changed. In this case it's required to reallocate the buffers.
        if has_payload_size_mismatch:
            print("PayloadSize has changed. Reallocating buffers...")

            is_data_stream_running = self.data_stream.IsGrabbing()
            if is_data_stream_running:
                self.data_stream.StopAcquisition()

            self.revoke_buffers()

            # Allocate and queue the buffers using the new "PayloadSize".
            self.alloc_buffers()

            if is_data_stream_running:
                self.data_stream.StartAcquisition()

        if not reconnect_information.IsRemoteDeviceAcquisitionRunning():
            self.remote_nodemap.FindNode("AcquisitionStart").Execute()

    def device_reconnected(self, device: ids_peak.Device,
                           reconnect_information: ids_peak.DeviceReconnectInformation):
        """
        When a device that was opened by the same application instance regains connection
        after a previous disconnect the 'Reconnected' event is triggered.

        The reconnect may (partially) fail, so we have to check the `DeviceReconnectInformation`
        class to know what steps are necessary to resume the acquistion.
        """
        print((
            "Device-Reconnected-Callback:\n"
            f"Key={device.Key()}\n"
            f"ReconnectSuccessful: {reconnect_information.IsSuccessful()}\n"
            f"RemoteDeviceAcquisitionRunning: {reconnect_information.IsRemoteDeviceAcquisitionRunning()}\n"
            f"RemoteDeviceConfigurationRestored: {reconnect_information.IsRemoteDeviceConfigurationRestored()}"
        ))

        # Using the `reconnectInformation` the user can tell whether they need to take actions
        # in order to resume the image acquisition.
        if reconnect_information.IsSuccessful():
            # Device was reconnected successfully, nothing to do.
            return

        self.ensure_compatible_buffers_and_restart_acquisition(
            reconnect_information)

    @staticmethod
    def device_disconnected(device: ids_peak.DeviceDescriptor):
        """
        Only called if the reconnect is enabled and if the device was previously opened by this
        application instance.
        """
        print(f"Disconnected-Callback: Key={device.Key()}")

    def register_callbacks(self):
        """
        Register the Devicemanager callbacks.

        Note: We have to store the callbacks, otherwise the callbacks will be unregistered because their
        lifetime is shorter than the device manager instance.
        """
        # ids_peak provides several events that you can subscribe to in order
        # to be notified when the connection status of a device changes.
        self.device_found_callback = self.device_manager.DeviceFoundCallback(
            self.device_found)
        self.device_found_callback_handle = self.device_manager.RegisterDeviceFoundCallback(
            self.device_found_callback)

        self.device_lost_callback = self.device_manager.DeviceLostCallback(
            self.device_lost)
        self.device_lost_callback_handle = self.device_manager.RegisterDeviceLostCallback(
            self.device_lost_callback)

        self.device_reconnected_callback = self.device_manager.DeviceReconnectedCallback(
            self.device_reconnected)
        self.device_reconnected_callback_handle = self.device_manager.RegisterDeviceReconnectedCallback(
            self.device_reconnected_callback)

        self.device_disconnected_callback = self.device_manager.DeviceDisconnectedCallback(
            self.device_disconnected)
        self.device_disconnected_callback_handle = self.device_manager.RegisterDeviceDisconnectedCallback(
            self.device_disconnected_callback)

    def unregister_callbacks(self):
        """
        Unregister the registered callbacks inside the Devicemanager
        """
        self.device_manager.UnregisterDeviceFoundCallback(
            self.device_found_callback_handle)
        self.device_manager.UnregisterDeviceLostCallback(
            self.device_lost_callback_handle)
        self.device_manager.UnregisterDeviceReconnectedCallback(
            self.device_reconnected_callback_handle)
        self.device_manager.UnregisterDeviceDisconnectedCallback(
            self.device_disconnected_callback_handle)

    def run_acquisition_loop(self):
        """
        Run the acquisition loop. The reconnect callback may abort this.
        """

        # Lock writeable nodes during acquisition
        self.remote_nodemap.FindNode("TLParamsLocked").SetValue(1)

        self.data_stream.StartAcquisition()
        self.remote_nodemap.FindNode("AcquisitionStart").Execute()
        self.remote_nodemap.FindNode("AcquisitionStart").WaitUntilDone()

        self.acquisition_running = True
        print("Starting acquisition...")
        print("Now you can disconnect or reboot the device to trigger a reconnect!")
        while self.acquisition_running:
            try:
                # Wait for finished/filled buffer event
                buffer = self.data_stream.WaitForFinishedBuffer(
                    ids_peak.Timeout.INFINITE_TIMEOUT)
                print(f"Received FrameID: {buffer.FrameID()}")
                # Put the buffer back in the pool, so it can be filled again
                self.data_stream.QueueBuffer(buffer)
            except KeyboardInterrupt:
                print("Keyboard interrupt.")
                break
            except Exception as e:
                print(f"Exception: {e}")

        print("Stopping acquisition...")
        self.remote_nodemap.FindNode("AcquisitionStop").Execute()
        self.remote_nodemap.FindNode("AcquisitionStop").WaitUntilDone()
        self.data_stream.StopAcquisition(
            ids_peak.AcquisitionStopMode_Default)

        # Unlock writeable nodes again
        self.remote_nodemap.FindNode("TLParamsLocked").SetValue(0)

    def open_device(self):
        # Open the first device
        device = None
        for dev in self.device_manager.Devices():
            if dev.IsOpenable(ids_peak.DeviceAccessType_Control):
                device = dev.OpenDevice(ids_peak.DeviceAccessType_Control)

        # Exit program if no device was found
        if not device:
            raise Exception("No device found. Exiting Program.")

        self.device = device

        print("Using Device " + self.device.DisplayName())
        self.remote_nodemap = self.device.RemoteDevice().NodeMaps()[0]
        self.data_stream = self.device.DataStreams()[0].OpenDataStream()

    def enable_reconnect(self):
        """
        We enable the reconnect by writing to the `ReconnectEnable` node
        in the `NodeMap` of the `System` that our device is connected to.
        """

        system_node_map = self.device.ParentInterface().ParentSystem().NodeMaps()[0]

        if not system_node_map.HasNode("ReconnectEnable"):
            raise SystemExit("No ReconnectEnable Node found!")

        reconnect_enable_node = system_node_map.FindNode("ReconnectEnable")
        reconnect_enable_access_status = reconnect_enable_node.AccessStatus()

        if reconnect_enable_access_status == ids_peak.NodeAccessStatus_ReadWrite:
            reconnect_enable_node.SetValue(True)
            return

        if reconnect_enable_access_status == ids_peak.NodeAccessStatus_ReadOnly:
            if reconnect_enable_node.Value():
                return

        raise SystemExit("Error: ReconnectEnable cannot be set to true!")

    def load_defaults(self):
        self.remote_nodemap.FindNode(
            "UserSetSelector").SetCurrentEntry("Default")
        # Same as UserSetSelector = Default; in cpp
        self.remote_nodemap.FindNode("UserSetLoad").Execute()
        # Same as UserSetLoad(); in cpp
        self.remote_nodemap.FindNode("UserSetLoad").WaitUntilDone()
        # Same as UserSetLoad(); in cpp
        # ...

        

        #
        

    def alloc_buffers(self):
        # Buffer size
        payload_size = self.remote_nodemap.FindNode("PayloadSize").Value()

        # Minimum number of required buffers
        buffer_count_max = self.data_stream.NumBuffersAnnouncedMinRequired()

        # Allocate buffers and add them to the pool
        for buffer_count in range(buffer_count_max):
            # Let the TL allocate the buffers
            buffer = self.data_stream.AllocAndAnnounceBuffer(payload_size)
            # Put the buffer in the pool
            self.data_stream.QueueBuffer(buffer)

    def revoke_buffers(self):
        # Remove buffers from any associated queue
        self.data_stream.Flush(ids_peak.DataStreamFlushMode_DiscardAll)

        for buffer in self.data_stream.AnnouncedBuffers():
            # Remove buffer from the transport layer
            self.data_stream.RevokeBuffer(buffer)

    def set_roi(self):
        # In order to restart the acquistion additonal steps are required:
        # see "The payload size might have changed." above
        self.remote_nodemap.FindNode("Height").SetValue(512)
        self.remote_nodemap.FindNode("Width").SetValue(512)

    def run(self):
        try:
            # Update the DeviceManager
            ids_peak.DeviceManager.Instance().Update()

            # Open first available device
            self.open_device()

            # Enable reconnect
            self.enable_reconnect()

            # Load default camera settings. This could be replaced with loading from sonfig files
            self.load_defaults()

            exposure_time = 50 # Ms

            self.remote_nodemap.FindNode("ExposureTime").SetValue(exposure_time)

            # NOTE: Uncommenting this line will modify the PayloadSize without saving the
            # changes in the UserSet. If the device reboots (e.g. by losing and then regaining
            # power) the PayloadSize will have changed, which means the acquisition on
            # the remote device will not be restarted.
            # self.set_roi()

            # Allocate buffers for the acquisition
            self.alloc_buffers()

            # Run acquisition loop until an error occurs or the user presses Ctrl+C
            self.run_acquisition_loop()

            # Revoke all buffers
            self.revoke_buffers()

        except ids_peak.AbortedException:
            print("Aborted")
        except Exception as e:
            print("EXCEPTION: " + str(e))
            return -2

        finally:
            self.unregister_callbacks()
            ids_peak.Library.Close()


if __name__ == '__main__':
    example = IDSCam()
    example.run()
