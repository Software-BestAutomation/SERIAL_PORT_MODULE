import threading
from datetime import datetime
from PySide6.QtCore import QObject, Signal

import utils.app_data as ad
from utils.serial_port import SerialPortHandler

class MainConnector(QObject):

    def __init__(self):

        super().__init__()
        
        self.serial_port = SerialPortHandler()
        
    # Testing
    def initialize_serial(self, connector=None):

        self.serial_port.connect(ad.comm_settings["port_name"], ad.comm_settings["baud_rate"], connector=connector)

        # self.serial_port.send_with_ack(1, 5)

    