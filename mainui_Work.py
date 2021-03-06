import sys
import asyncio
import json
from typing import TextIO
from qasync import QEventLoop
from bleak import BleakScanner, BleakClient, discover
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData
import GuiTags
from PyQt5 import QtCore, QtGui, QtWidgets, uic
from PyQt5.QtCore import QDate, QTime, QDateTime, Qt
from PyQt5.QtWidgets import QMessageBox
from util import *
import queue
import Sensors
import time
import wgs_lpp_parser
from mqtt_client import WgsMqttClient
import mqtt_dialog
import math
import csv


class MyTable(object):
    """
    import sys
    import GuiTags
    from PyQt5 import QtCore, QtGui, QtWidgets, uic
    self variable is used to bind the instance of the class to the instance method.
     We have to explicitly declare it as the first method argument to access the instance variables and methods.
    The self variable gives us access to the current instance properties
     provide standard table display facilities for applications.
    """

    def __init__(self, window_object, object_name):
        self.table = window_object.findChild(QtWidgets.QTableWidget, object_name)
        self.tableRowCount = 0
        self.windowObject = window_object
        self.table.key_press_event = self.key_press_event

    def key_press_event(self, event):
        if event.key() == QtCore.Qt.Key_C and event.modifiers() & QtCore.Qt.ControlModifier:
            self.copy()

    def copy(self):
        items = self.table.selectedItems()
        for item in items:
            QtWidgets.QApplication.clipboard().clear()
            QtWidgets.QApplication.clipboard().setMimeData(item.text)

    def add_row_into_table(self, elem):
        self.tableRowCount += 1
        self.update_row_count()
        column = 0
        for e in elem:
            self.table.setItem(self.tableRowCount - 1, column,
                               QtWidgets.QTableWidgetItem(str(e)))
            column += 1

    def update_row_count(self):
        self.table.setRowCount(self.tableRowCount)

    def clean_table(self):
        self.tableRowCount = 0
        self.update_row_count()

    def current_row(self):
        row = self.table.currentRow()
        return row

    def item(self, x, y):
        return self.table.item(x, y)


class BleDevice:
    def __init__(self):
        self.address = None
        self.name = None
        self.heared = False
        self.connected = False
        self.app = 0
        self.client = None


def is_hex(s):
    """checking for valid hexadecimal digits"""
    try:
        int(s, 16)
        return True
    except ValueError:
        return False


class Ui(QtWidgets.QMainWindow):
    '''
    put all the stuff that we want in our table
    Button presses and modifying elements that we have already put on to the table'''

    def __init__(self, loop):
        super(Ui, self).__init__()
        uic.loadUi("MainUI.ui", self)

        self.loop = loop
        self.eggDataTable = MyTable(self, GuiTags.DATA_TABLE)
        self.findChild(QtWidgets.QPushButton, GuiTags.CLEAN_DATA_TABLE_BUTTON).clicked.connect(
            self.eggDataTable.clean_table)

        self.scanTable = MyTable(self, GuiTags.SCAN_TABLE)

        self.scanAdvParserTable = MyTable(self, GuiTags.SCAN_PARSE_ADV_TABLE)

        self.scanButton = self.findChild(
            QtWidgets.QPushButton, GuiTags.SCAN_BUTTON)
        self.scanButton.clicked.connect(self.start_scan)

        self.connectButton = self.findChild(
            QtWidgets.QPushButton, GuiTags.CONNECT_BUTTON)
        self.connectButton.clicked.connect(self.start_connect)

        self.scanProgressBar = self.findChild(
            QtWidgets.QProgressBar, GuiTags.SCAN_PROGRESS_BAR)

        self.connectionLabel = self.findChild(
            QtWidgets.QLabel, GuiTags.CONNECTION_STATUS_LABEL)

        self.ScanButtonPressed = False

        self.bleDevice = BleDevice()

        '''Configuration'''
        self.configListApp = self.findChild(
            QtWidgets.QListWidget, GuiTags.CONFIG_LIST_APP)
        self.configAppButton = self.findChild(
            QtWidgets.QPushButton, GuiTags.CONFIG_PROGRAM_BUTTON_APP)

        self.configDevEUIButton = self.findChild(
            QtWidgets.QPushButton, GuiTags.CONFIG_BUTTON_DEVEUI)
        self.configDevEUIButton.clicked.connect(
            lambda: self.program_device(GuiTags.BleConfigParam.DEV_EUI))

        self.configMeasureIntervalButton = self.findChild(
            QtWidgets.QPushButton, GuiTags.CONFIG_PROGRAM_BUTTON_MEASURE_INTERVAL)
        self.configMeasureIntervalButton.clicked.connect(
            lambda: self.program_device(GuiTags.BleConfigParam.MEASURE_INTERVAL))

        self.configAppKeyButton = self.findChild(
            QtWidgets.QPushButton, GuiTags.CONFIG_PROGRAM_BUTTON_APP_KEY)
        self.configAppKeyButton.clicked.connect(
            lambda: self.program_device(GuiTags.BleConfigParam.APP_KEY))

        self.configAppKeyField = self.findChild(
            QtWidgets.QTextEdit, GuiTags.CONFIG_FIELD_APP_KEY)
        # self.configAppKeyField.textChanged.connect(self.trimLoRaAppKeyInput)

        self.configStartButton = self.findChild(
            QtWidgets.QPushButton, GuiTags.CONFIG_PROGRAM_BUTTON_START)
        self.configStartButton.clicked.connect(
            lambda: self.program_device(GuiTags.BleConfigParam.START))

        self.configStopButton = self.findChild(
            QtWidgets.QPushButton, GuiTags.CONFIG_PROGRAM_BUTTON_STOP)
        self.configStopButton.clicked.connect(
            lambda: self.program_device(GuiTags.BleConfigParam.STOP))

        """MQTT API"""

        self.configMQTTConfigMenuInterface = self.findChild(
            QtWidgets.QAction, GuiTags.MENU_INTERFACE_MQTT)
        self.configMQTTConfigMenuInterface.triggered.connect(
            self.launch_mqtt_config)

        self.publishMQTTButton = self.findChild(
            QtWidgets.QPushButton, GuiTags.PUBLISH_MQTT_LABEL)
        self.publishMQTTButton.clicked.connect(self.publish_data_via_mqtt)

        self.exportButton = self.findChild(
            QtWidgets.QPushButton, GuiTags.EXPORT_TO_CSV_BUTTON)
        self.exportButton.clicked.connect(self.export_csv)

    def export_csv(self):
        """
        Exporting eggDataTable to CSV file "eggDataTable.csv"
        """
        data = []
        for i in range(0, self.eggDataTable.tableRowCount):
            row = [self.eggDataTable.item(i, j).text() for j in range(0, 5)]
            data.append(row)
        with open('eggDataTable.csv', 'w+', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['Address', 'Time', 'Sensor Type', 'Channel', 'value'])
            writer.writerows(data)
        print("CSV Created")

    def publish_data_via_mqtt(self):
        wgsmqttcl = WgsMqttClient()
        client = wgsmqttcl.connect_mqtt()
        #client = WgsMqttClient.connect_mqtt()
        """Opening JSON file"""
        jsonArr = self.json_generator_from_egg_table_row()
        jsonArr = sorted(jsonArr, key=lambda k: ['timestamp'], reverse=True)
        lastTs = jsonArr[0]['timestamp']
        for e in jsonArr:
            currTs = e['timestamp']
            time.sleep(currTs - lastTs)
            client.publish(client, json.dumps(e))
            lastTs = currTs

    def json_generator_from_egg_table_row(self):
        body = []
        for i in range(0, self.eggDataTable.tableRowCount):
            row = [self.eggDataTable.item(i, j).text() for j in range(0, 5)]
            x = {
                "device_eui": row[0],
                "timestamp": int(row[1]),
                "data": {
                    "channel": int(row[3]),
                    "name": "",
                    "type": int(row[2]),
                    "value": float(row[4])
                }
            }
            body.append(x)
        return json.dumps(body)


    def launch_mqtt_config(self):
        dialog = QtWidgets.QDialog()
        dialog.ui = mqtt_dialog.Ui_mqttConfig()
        dialog.ui.setupUi(dialog, self.findChild(
            QtWidgets.QLabel, GuiTags.STATUS_MQTT_LABEL))
        dialog.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        dialog.exec_()

    def program_device(self, ble_config_param):
        if not self.bleDevice.connected:
            """there is no Bluetooth connection,
            click on this Button show the messageBox in clickMethode()function"""
            self.configDevEUIButton.clicked.connect(self.clickMethod)
            self.configProgramButtonAppKey.clicked.connect(self.clickMethod)
            self.configProgramButtonMeasureInterval.clicked.connect(self.clickMethod)

            print("Device not connected")
        else:
            if ble_config_param == GuiTags.BleConfigParam.START:
                data = convert_int_in_bytes(int(time.time()))
                data.insert(0, GuiTags.BleConfigParam.TIME.value)
                print("Set time")
                asyncio.ensure_future(self.write_chars(GuiTags.WGS_CONFIG_UUID, data, disconnect=False), loop=self.loop)
                print('Start Device')
                data = [GuiTags.BleConfigParam.START.value, 0x99]
                asyncio.ensure_future(self.write_chars(GuiTags.WGS_CONFIG_UUID, data, disconnect=True), loop=self.loop)
            elif ble_config_param == GuiTags.BleConfigParam.STOP:
                print('Stop Device')
                data = [GuiTags.BleConfigParam.STOP.value, 0x10]
                asyncio.ensure_future(self.write_chars(GuiTags.WGS_CONFIG_UUID, data, disconnect=False), loop=self.loop)

            ######Config Application Type######

            # Config Measure Interval
            elif ble_config_param == GuiTags.BleConfigParam.MEASURE_INTERVAL:
                try:
                    measure_interval = int(self.findChild(
                        QtWidgets.QTextEdit, GuiTags.CONFIG_FIELD_MEASURE_INTERVAL).toPlainText())
                    print("Measure Intervall", measure_interval)
                except:
                    """"return:Error: entering a non-integer data such as Alphabet, mathematical operators and...  """
                    QMessageBox.about(self, "ERROR", "illegal input")
            # Config LoRaWAN APPKey
            elif ble_config_param == GuiTags.BleConfigParam.APP_KEY:
                rawdata = self.findChild(QtWidgets.QTextEdit, GuiTags.CONFIG_FIELD_APP_KEY).toPlainText()
                if len(rawdata) == 32:
                    if is_hex(rawdata):
                        data = [int(rawdata[i:i + 2], 16) for i in range(0, len(rawdata), 2)]
                        data.insert(0, GuiTags.BleConfigParam.APP_KEY.value)
                        asyncio.ensure_future(self.write_chars(GuiTags.WGS_CONFIG_UUID, data), loop=self.loop)
                        print('The app key has been transferred')
                    else:
                        """"Return:Error: when the input is not hex"""
                        QMessageBox.about(self, "Warning", "the number is not hex")
                else:
                    """"Return:Error of not being a 32 length string"""
                    QMessageBox.about(self, "Warning", "The entered EUI has invalid length")
                    """which one is better? 
                    QMessageBox.information(self, "info", "Enter an 32-length number")"""

            elif ble_config_param == GuiTags.BleConfigParam.SENSOR_TYPE:
                pass
            elif ble_config_param == GuiTags.BleConfigParam.DEV_EUI:
                rawdata = self.findChild(QtWidgets.QTextEdit, GuiTags.CONFIG_FIELD_DEVEUI).toPlainText()
                if len(rawdata) == 16:
                    if is_hex(rawdata):
                        data = [int(rawdata[i:i + 2], 16) for i in range(0, len(rawdata), 2)]
                        data.insert(0, GuiTags.BleConfigParam.DEV_EUI.value)
                        asyncio.ensure_future(self.write_chars(GuiTags.WGS_CONFIG_UUID, data), loop=self.loop)
                        print('The Dev EUI has been transferred')
                    else:
                        """"Return:Error warning: when the input is not hex"""
                        QMessageBox.about(self, "Warning", "the number is not hex")
                else:
                    """"Return:Error of not being a 16 length string"""
                    QMessageBox.about(self, "Warning", "The entered EUI has invalid length")

    def clickMethod(self):
        """when BLEdevice is not connected. Click on any of this Buttons show an Error:
        DevEUIButton:program
        ProgramButtonAppKey:program
        ProgramButtonMeasureInterval:program
        """
        QMessageBox.about(self, "Error", "Device is not Connected")

    def start_scan(self):
        self.ScanButtonPressed = True
        self.scanTable.clean_table()
        if self.findChild(QtWidgets.QRadioButton, GuiTags.CONNECTION_CHOICE_JUST_SCAN).isChecked():
            asyncio.ensure_future(self.scan_and_parse(), loop=self.loop)

        else:
            asyncio.ensure_future(self.progress_bar(), loop=self.loop)
            asyncio.ensure_future(self.start_ble_scan(), loop=self.loop)

    async def write_chars(self, uuid, data, disconnect=False):
        await self.bleDevice.client.write_gatt_char(uuid, data)
        if disconnect:
            await self.bleDevice.client.disconnect()
            self.set_connection_status_disconnected()

    def scanner_callback_parse_adv(self, device: BLEDevice, advertisement_data: AdvertisementData):
        all_data = advertisement_data.all_data
        if all_data is None:
            return
        for i in range(0, len(all_data)):
            if len(all_data) < i + 4:
                break
            if all_data[i] == GuiTags.WGS_ADV_PREAMBLE[0] and all_data[i + 1] == GuiTags.WGS_ADV_PREAMBLE[1] and \
                    all_data[
                        i + 2] == GuiTags.WGS_ADV_PREAMBLE[2] and all_data[i + 3] == GuiTags.WGS_ADV_PREAMBLE[3]:

                for lpp in wgs_lpp_parser.parse_byte_array(all_data[i + 4:]):
                    self.scanAdvParserTable.add_row_into_table([int(time.time()), lpp.channel, lpp.name, lpp.value_f])

    async def scan_and_parse(self):
        scanner = BleakScanner()
        scanner.register_detection_callback(self.scanner_callback_parse_adv)
        await scanner.start()
        await asyncio.sleep(5.0)
        await scanner.stop()

    async def progress_bar(self):
        count = 0
        for i in range(0, 5):
            await asyncio.sleep(int(2))
            count += 20

            self.scanProgressBar.setValue(count)

    async def start_ble_scan(self):
        """
           calling start and stop methods on the scanner
           The <BleakScanner> bleak.backends.scanner.BleakScanner class is used to discover Bluetooth Low Energy devices.
           The list of objects returned by the discover method are instances of bleak.backends.
           device.BLEDevice has name, address and rssi attributes, as well as a metadata attribute,
           a dict with keys uuids and manufacturer_data which potentially
           contains a list of all service UUIDs on the device and a binary string of data from the manufacturer of the device respectively.
           return: discovering Bluetooth devices with  address, name and rssi that can be connected to
           """
        print('Start Scan')
        scanner = BleakScanner()
        await scanner.start()
        await asyncio.sleep(5.0)
        await scanner.stop()

        new_row = [0, 0, 0]
        for d in scanner.discovered_devices:
            new_row[0] = d.address
            new_row[1] = d.name
            new_row[2] = d.rssi
            self.scanTable.add_row_into_table(new_row)

    def start_connect(self):
        asyncio.ensure_future(self.start_connect_(), loop=self.loop)

    async def start_connect_(self):
        print("Start connect")
        mac_addr = self.scanTable.item(self.scanTable.current_row(), 0).text()
        client = BleakClient(mac_addr)
        try:
            await client.connect()
            self.scanProgressBar.setValue(100)
            svcs = await client.get_services()
            print("Services:")
            for service in svcs:
                print(service)
                for c in service.characteristics:
                    if c.handle == 22:
                        GuiTags.WGS_CONFIG_UUID = c.uuid
                    if c.handle == 25:
                        GuiTags.WGS_DATA_UUID = c.uuid
            self.set_connection_status_connected(client)
        except Exception as e:
            self.set_connection_status_disconnected()
            self.scanProgressBar.setValue(0)

    def set_connection_status_connected(self, client):
        """"Connection Clients
            changing the status to "connected" after connecting to Bluetooth Device

            is_checheded():This property holds whether the button is checked.Only checkable buttons can be checked.
             By default, the button is unchecked.
            Check connection status between this client and the server. Returns Boolean representing
            connection status.
             """
        self.bleDevice.client = client
        self.bleDevice.connected = True
        self.connectionLabel.setText("Connected")
        self.connectionLabel.setStyleSheet('color: green')
        if self.findChild(QtWidgets.QRadioButton, GuiTags.CONNECTION_CHOICE_DATA).isChecked():
            asyncio.ensure_future(self.wait_for_data(), loop=self.loop)

    def set_connection_status_disconnected(self):
        """ the status of connection Button by default and when is not connected
        """
        self.bleDevice.client = None
        self.bleDevice.connected = False
        self.connectionLabel.setText("Disconnected")
        self.connectionLabel.setStyleSheet('color: red')

    def notification_handler(self, sender, data):
        int_values = [x for x in data]
        print(int_values)
        new_row = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        new_row[0] = convert_int_in_hex_string(int_values[0:4])
        new_row[1] = convert_bytes_in_int_lsb2(int_values[4:], 4)
        new_row[2] = int_values[8]  # Type
        new_row[3] = int_values[9]  # Channel
        new_row[4] = convert_bytes_in_int_lsb2(int_values[12:],
                                               Sensors.get_value_size(Sensors.SENSOR_TYPES(new_row[2])))
        print(int_values, " | ", new_row)

        self.eggDataTable.add_row_into_table(new_row)

    async def wait_for_data(self):
        await self.bleDevice.client.start_notify(GuiTags.WGS_DATA_UUID, self.notification_handler)
        await asyncio.sleep(5.0)
        await self.bleDevice.stop_notify(GuiTags.WGS_DATA_UUID)


if __name__ == "__main__":
    '''app:giving some kind of config set up 
    Every PyQt5 application must create an application object. 
    The sys.argv parameter is a list of arguments from a command line.'''
    app = QtWidgets.QApplication(sys.argv)
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)
    window = Ui(loop)
    window.show()
    # app.exec_()
    with loop:
        loop.run_forever()
