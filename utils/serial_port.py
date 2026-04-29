import serial
import threading
import time
from datetime import datetime, timedelta
import re

import utils.app_data as ad
import utils.commands as cmd

class SerialPortHandler:

    def __init__(self):
        self.ser = None
        self.is_connected = False
        self.receive_thread = None
        self.connector = None

    # 1. Connect
    def connect(self, port="COM3", baudrate=9600, timeout=1, connector = None):
        try:
            self.ser = serial.Serial(port, baudrate, timeout=timeout)
            self.is_connected = True
            print(f"Connected to {port} at {baudrate} baud.")
            self.connector = connector
            # Start receiving in a background thread
            self.receive_thread = threading.Thread(target=self.receive_data, daemon=True)
            self.receive_thread.start()
        except Exception as e:
            print(f"Connection failed: {e}")
            self.is_connected = False

    # 2. Disconnect
    def disconnect(self):
        if self.ser and self.ser.is_open:
            self.ser.close()
        self.is_connected = False
        print("Disconnected from serial port.")

    # 3. Send data
    def send_data(self, data: str):
        if self.is_connected and self.ser:
            try:
                self.ser.write(f"{data}\r\n".encode())
                print(f"Sent: {data}")
            except Exception as e:
                print(f"Send failed: {e}")
                self._handle_disconnect()
        else:
            print("Not connected. Cannot send data.")

    # 4. Receive data (runs continuously while connected)
    def receive_data(self):

        while self.is_connected and self.ser:

            try:
                if self.ser.in_waiting > 0:
                    data = self.ser.readline().decode(errors="ignore").strip()
                    if data:
                        print(f"Received: {data}")
                        threading.Thread(
                            target=self.process_incoming_command, args=(data, self.connector), daemon=True
                        ).start()

                else:
                    time.sleep(0.1)  # avoid busy loop

            except Exception as e:
                print(f"Receive failed: {e}")
                self._handle_disconnect()
                break

    # 5. Get connection status
    def get_status(self):
        return self.is_connected
    
    # 6. Get all available ports
    def get_available_ports(self):
        ad.port_names = [port.device for port in serial.tools.list_ports.comports()]
        print(f"Available ports: {ad.port_names}")
        return ad.port_names

    # Internal helper to handle unexpected disconnects
    def _handle_disconnect(self):
        if self.ser:
            try:
                self.ser.close()
            except:
                pass
        self.is_connected = False
        print("⚠️ Serial port disconnected unexpectedly.")

    # Send Command with Acknowledgment Handling
    def send_with_ack(self, cmd_id, delay=1):

        print("SENDING")

        cmd.SW_COMMANDS[cmd_id]["sent"] = False # Resets the flag

        time_out = datetime.now() + timedelta(seconds=60) # 60 seconds timeout for ack

        while True: # Loop until timeout

            if cmd_id not in cmd.SW_COMMANDS: # Check whether command ID exists
                cmd.SW_COMMANDS[cmd_id]["sent"] = False
                cmd.SW_COMMANDS[cmd_id]["err_msg"] = f"COMMAND ID: {cmd_id} NOT FOUND"
                break

            if not datetime.now() < time_out:
                cmd.SW_COMMANDS[cmd_id]["sent"] = False
                cmd.SW_COMMANDS[cmd_id]["err_msg"] = f"COMMAND: {cmd.SW_COMMANDS[cmd_id]['cmd']} TIMED OUT! NO ACKNOWLEDGMENT RECEIVED!"
                break

            cmd_data = cmd.SW_COMMANDS[cmd_id] # Get command data for the given ID

            cmd_type = cmd_data["cmd_type"] # Get Command Type for the given ID

            can_send = False # Can Send command Flag

            if ad.current_work_data["IS_PROCESS_RUNNING"]: # Check Whether the main process is running or not
                if cmd_type in [1, 2]: # Check Whether the command type is acceptable based on main process status.
                    can_send = True # Set Can Send Flag as True

            else:
                if cmd_type in [0, 2]: # Check Whether the command type is acceptable based on main process status.
                    can_send = True # Set Can Send Flag as True

            if not can_send: # If Can Send is False then sending command is blocked
                cmd.SW_COMMANDS[cmd_id]["sent"] = False
                cmd.SW_COMMANDS[cmd_id]["err_msg"] = f"CANNOT SEND COMMAND {cmd_data['cmd']} (COMMAND TYPE: {cmd_type}) DUE TO PROCESS STATE: {ad.current_work_data['IS_PROCESS_RUNNING']}"
                break

            if self.is_connected: # Check if Controller is connected

                if cmd_data["is_ack"]: # If ack received, exit
                    cmd.SW_COMMANDS[cmd_id]["sent"] = True
                    break

                else:
                    self.send_data(cmd_data["cmd"]) # Send command to Controller

                time.sleep(delay) # Wait before checking for ack and resending

            else: # No client connected
                cmd.SW_COMMANDS[cmd_id]["sent"] = False
                cmd.SW_COMMANDS[cmd_id]["err_msg"] = f"NO CLIENT CONNECTED TO SEND COMMAND"
                break

        cmd.SW_COMMANDS[cmd_id]["is_ack"] = False  # Reset ack for next use
        return True

    def process_incoming_command(self, command_str, connector):
        # Use regex to find all patterns starting with $ and ending with #
        # The [^#]+ ensures we capture everything except the delimiter in between
        commands = re.findall(r'\$[^\#]+\#', command_str)

        if not commands:
            # Fallback if the string doesn't follow the $...# format strictly
            # or if it's a single command without those delimiters
            commands = [command_str]

        for individual_cmd in commands:
            self._execute_command_logic(individual_cmd, connector)

    # Process Incoming Command
    def _execute_command_logic(self, command_str, connector):

        cmd_data = cmd.CTRLR_COMMANDS.get(command_str) # Lookup command in CTRLR_COMMANDS

        matched_prefix = None

        if not cmd_data:
            matched_prefix, cmd_data = next(((prefix, data) for prefix, data in cmd.CTRLR_COMMANDS.items() if command_str.startswith(prefix)), (None, None)) # Check whether the Command in matching with starting string

        if cmd_data: # Match found in CTRLR_COMMANDS cmds

            ack = cmd_data['ack'] # Get corresponding ack
            self.send_data(ack) # Send ack back to client

            cmd_type = cmd_data['cmd_type'] # Get corresponding Command Type

            can_do_action = False # Flag for Processing Command

            if ad.current_work_data['IS_PROCESS_RUNNING']: # Check Whether the main process is running or not
                if cmd_type in [1, 2]: # Check Whether the command type is acceptable based on main process status.
                    can_do_action = True # Set Processing Command Flag as True

            else:
                if cmd_type in [0, 2]: # Check Whether the command type is acceptable based on main process status.
                    can_do_action = True # Set Processing Command Flag as True

            if not can_do_action: # If Processing Command is False then process is blocked
                print(f"⚠️ CANNOT PROCESS COMMAND: {command_str} DUE TO PROCESS STATE: {ad.current_work_data['IS_PROCESS_RUNNING']}")
                return

            print(f"✅ PROCESSING COMMAND: {command_str}")

           # Resolve action string into MainConnector method
            action_name = cmd_data.get("action")

            if action_name and hasattr(connector, action_name):

                try:

                    func = getattr(connector, action_name)

                    if "args" in cmd_data or matched_prefix:

                        _args = None

                        if "args" in cmd_data:

                            _args = cmd_data['args']

                        # If this was a prefix match, parse payload into args
                        # if matched_prefix:
                        #     payload = command_str[len(matched_prefix):]

                        #     # Example: split by commas, strip trailing '#'
                        #     payload = payload.strip("#")
                        #     payload = payload.strip("$")

                        #     if payload:
                        #         parsed_args = payload.split(",")
                        #         # Merge with any predefined args
                        #         _args = _args + parsed_args

                        # If it's a string, wrap it in a tuple
                        if isinstance(_args, str):
                            _args = (_args,)

                        threading.Thread(target=func, args=_args, daemon=True).start()

                    else:

                        threading.Thread(target=func, daemon=True).start() # Call the function

                except Exception as e:
                    print(f"⚠️ ERROR EXECUTING ACTION: {e}")

            return

        ACK_LOOKUP = {v['ack']: k for k, v in cmd.SW_COMMANDS.items()} # Lookup acks in SW_COMMANDS

        if command_str in ACK_LOOKUP: # Match found in SW_COMMANDS acks

            cmd_id = ACK_LOOKUP[command_str] # Get command ID from ack

            cmd_type = cmd.SW_COMMANDS[cmd_id]['cmd_type'] # Get corresponding Command Type

            can_ack = False # Flag for Acknowledging

            cmd.SW_COMMANDS[cmd_id]['is_ack'] = True # Mark ack as received

            print(f"✅ ACK RECEIVED: {command_str}")

            if ad.current_work_data['IS_PROCESS_RUNNING']: # Check Whether the main process is running or not
                if cmd_type in [1, 2]: # Check Whether the command type is acceptable based on main process status.
                    can_ack = True # Set Acknowledging Flag as True

            else:
                if cmd_type in [0, 2]: # Check Whether the command type is acceptable based on main process status.

                    can_ack = True # Set Acknowledging Flag as True

                    action_name = cmd.SW_COMMANDS[cmd_id].get("action")

                    if action_name and hasattr(connector, action_name):
                        func = getattr(connector, action_name)
                        threading.Thread(target=func, args=(cmd_id,), daemon=True).start()

            if not can_ack: # If Acknowledging is False then acknowledgment is blocked
                print(f"⚠️ CANNOT ACCCEPT ACKNOWLEDGEMENT: {command_str} DUE TO PROCESS STATE: {ad.current_work_data['IS_PROCESS_RUNNING']}")
                return

            return

# # Example usage
# if __name__ == "__main__":

#     handler = SerialPortHandler()

#     handler.connect(port=ad.comm_settings["port_name"], baudrate=ad.comm_settings["baud_rate"])

#     handler.send_data("$START#")

#     try:
#         while handler.get_status():
#             time.sleep(1)
#     except KeyboardInterrupt:
#         handler.disconnect()
