# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'MainUI.ui'
#
# Created by: PyQt5 UI code generator 5.15.4
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.

import sys
import asyncio
import string
from typing import TextIO

from qasync import QEventLoop
from bleak import BleakScanner, BleakClient, discover
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData
import GuiTags
from PyQt5 import QtCore, QtGui, QtWidgets, uic
from util import *
import queue
import Sensors
import time
import wgs_lpp_parser
from mqtt_client import wgs_mqtt_client
import mqtt_dialog
import math
import csv


class MyTable(object):
    def __init__(self, windowObject, objectName):
        self.table = windowObject.findChild(QtWidgets.QTableWidget, objectName)
        self.tableRowCount = 0
        self.windowObject = windowObject
        self.table.keyPressEvent = self.keyPressEvent

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_C and event.modifiers() & QtCore.Qt.ControlModifier:
            self.copy()

    def copy(self):
        items = self.table.selectedItems()
        for item in items:
            QtWidgets.QApplication.clipboard().clear()
            QtWidgets.QApplication.clipboard().setMimeData(item.text)

    def addRowInToTable(self, elem):
        self.tableRowCount += 1
        self.updateRowCount()
        column = 0
        for e in elem:
            self.table.setItem(self.tableRowCount - 1, column,
                               QtWidgets.QTableWidgetItem(str(e)))
            column += 1

    def updateRowCount(self):
        self.table.setRowCount(self.tableRowCount)

    def cleanTable(self):
        self.tableRowCount = 0
        self.updateRowCount()

    def currentRow(self):
        row = self.table.currentRow()
        return row

    def item(self, x, y):
        return self.table.item(x, y)

    # myFile = open('myFile.csv', 'w')
    # with myFile:
    # writer = csv.writer(myFile)
    # writer.writerows(row)
    # print(myFile)
    def export_csv(self):
        def export_csv(self):
            for i in range(0, self.eggDataTable.tableRowCount):
                row = []
                for j in range(0, 4):
                    row.append(self.eggDataTable.item(i, j).text())
                    with open('odd.csv', 'w+', newline='') as file:
                        writer = csv.writer(file)
                        writer.writerows(row)
                        file.close()


class BLE_Device():
    def __init__(self):
        self.address = None
        self.name = None
        self.heared = False
        self.connected = False
        self.app = 0
        self.client = None


class Ui(QtWidgets.QMainWindow):
    def __init__(self, loop):
        super(Ui, self).__init__()
        uic.loadUi("MainUI.ui", self)

        self.loop = loop
        self.eggDataTable = MyTable(self, GuiTags.DATA_TABLE)
        self.findChild(QtWidgets.QPushButton, GuiTags.CLEAN_DATA_TABLE_BUTTON).clicked.connect(self.fillDummyData)

        self.scanTable = MyTable(self, GuiTags.SCAN_TABLE)

        self.scanAdvParserTable = MyTable(self, GuiTags.SCAN_PARSE_ADV_TABLE)

        self.scanButton = self.findChild(
            QtWidgets.QPushButton, GuiTags.SCAN_BUTTON)
        self.scanButton.clicked.connect(self.startScan)

        self.connectButton = self.findChild(
            QtWidgets.QPushButton, GuiTags.CONNECT_BUTTON)
        self.connectButton.clicked.connect(self.startConnect)

        self.scanProgressBar = self.findChild(
            QtWidgets.QProgressBar, GuiTags.SCAN_PROGRESS_BAR)

        self.cleanScanTableButton = self.findChild(
            QtWidgets.QPushButton, 'cleanScanTableButton')
        self.cleanScanTableButton.clicked.connect(self.scanTable.cleanTable)

        self.exportToCsvButton = self.findChild(
            QtWidgets.QPushButton, 'exportToCsvButton')
        self.exportToCsvButton.clicked.connect(self.eggDataTable.export_csv())

        self.connectionLabel = self.findChild(
            QtWidgets.QLabel, GuiTags.CONNECTION_STATUS_LABEL)

        self.ScanButtonPressed = False

        self.bleDevice = BLE_Device()

        '''Configuration'''
        self.configListApp = self.findChild(
            QtWidgets.QListWidget, GuiTags.CONFIG_LIST_APP)
        self.configAppButton = self.findChild(
            QtWidgets.QPushButton, GuiTags.CONFIG_PROGRAM_BUTTON_APP)

        self.configDevEUIButton = self.findChild(
            QtWidgets.QPushButton, GuiTags.CONFIG_BUTTON_DEVEUI)
        self.configDevEUIButton.clicked.connect(
            lambda: self.programmDevice(GuiTags.BLE_CONFIG_PARAM.DEV_EUI))

        self.configMeasureIntervalButton = self.findChild(
            QtWidgets.QPushButton, GuiTags.CONFIG_PROGRAM_BUTTON_MEASURE_INTERVAL)
        self.configMeasureIntervalButton.clicked.connect(
            lambda: self.programmDevice(GuiTags.BLE_CONFIG_PARAM.MEASURE_INTERVAL))

        self.configAppKeyButton = self.findChild(
            QtWidgets.QPushButton, GuiTags.CONFIG_PROGRAM_BUTTON_APP_KEY)
        self.configAppKeyButton.clicked.connect(
            lambda: self.programmDevice(GuiTags.BLE_CONFIG_PARAM.APP_KEY))

        self.configAppKeyField = self.findChild(
            QtWidgets.QTextEdit, GuiTags.CONFIG_FIELD_APP_KEY)
        # self.configAppKeyField.textChanged.connect(self.trimLoRaAppKeyInput)

        self.configSensorsButton = self.findChild(
            QtWidgets.QPushButton, GuiTags.CONFIG_PROGRAM_BUTTON_SENSORS)
        self.configSensorsButton.clicked.connect(
            lambda: self.programmDevice(GuiTags.BLE_CONFIG_PARAM.SENSOR_TYPE))

        self.configStartButton = self.findChild(
            QtWidgets.QPushButton, GuiTags.CONFIG_PROGRAM_BUTTON_START)
        self.configStartButton.clicked.connect(
            lambda: self.programmDevice(GuiTags.BLE_CONFIG_PARAM.START))

        self.configSetTimeButton = self.findChild(
            QtWidgets.QPushButton, GuiTags.CONFIG_PROGRAM_BUTTON_TIME)
        self.configSetTimeButton.clicked.connect(
            lambda: self.programmDevice(GuiTags.BLE_CONFIG_PARAM.TIME))

        """MQTT API"""

        self.configMQTTConfigMenuInterface = self.findChild(
            QtWidgets.QAction, GuiTags.MENU_INTERFACE_MQTT)
        self.configMQTTConfigMenuInterface.triggered.connect(
            self.launchMQTTConfig)

        self.publishMQTTButton = self.findChild(
            QtWidgets.QPushButton, GuiTags.PUBLISH_MQTT_LABEL)
        self.publishMQTTButton.clicked.connect(self.publishEggDataViaMQTT)

    ##DUMMY DATA TEST
    # self.fillDummyData()


    def publishEggDataViaMQTT(self):
        statusMQTT = wgs_mqtt_client.connected
        while (statusMQTT == False):
            self.launchMQTTConfig()
            time.sleep(1)
            statusMQTT = wgs_mqtt_client.connected

        self.findChild(
            QtWidgets.QLabel, GuiTags.STATUS_MQTT_LABEL).setText("Connection MQTT: Connected")
        for i in range(0, self.eggDataTable.tableRowCount):
            row = []
            for j in range(0, 5):
                row.append(self.eggDataTable.item(i, j).text())
            str = wgs_mqtt_client.jsonGeneratorFromEggTableRow(row)
            wgs_mqtt_client.publishNewData(str)

    def launchMQTTConfig(self):
        dialog = QtWidgets.QDialog()
        dialog.ui = mqtt_dialog.Ui_mqttConfig()
        dialog.ui.setupUi(dialog, self.findChild(
            QtWidgets.QLabel, GuiTags.STATUS_MQTT_LABEL))
        dialog.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        dialog.exec_()

    def programmDevice(self, ble_config_param):

        if self.bleDevice.connected == False:
            print("Device not connected")
        else:
            if ble_config_param == GuiTags.BLE_CONFIG_PARAM.START:
                print('Start Device')
                data = [GuiTags.BLE_CONFIG_PARAM.START.value, 0x99]
                asyncio.ensure_future(self.writeChars(GuiTags.WGS_CONFIG_UUID, data, disconnect=True), loop=self.loop)
            elif ble_config_param == GuiTags.BLE_CONFIG_PARAM.TIME:
                print('Set Time Device')
                data = convert_int_in_bytes(int(time.time()))
                data.insert(0, GuiTags.BLE_CONFIG_PARAM.TIME.value)
                asyncio.ensure_future(self.writeChars(GuiTags.WGS_CONFIG_UUID, data, disconnect=False), loop=self.loop)
            ######Config Application Type######
            elif ble_config_param == GuiTags.BLE_CONFIG_PARAM.APP_TYPE:
                print('Set Application Type')
                data = self.configListApp.currentRow()
                asyncio.ensure_future(self.writeChars(GuiTags.WGS_CONFIG_UUID, data, disconnect=False), loop=self.loop)
            # Config Measure Interval
            elif ble_config_param == GuiTags.BLE_CONFIG_PARAM.MEASURE_INTERVAL:
                try:
                    measureIntervall = int(self.findChild(
                        QtWidgets.QTextEdit, GuiTags.CONFIG_FIELD_MEASURE_INTERVAL).toPlainText())
                    print("Measure Intervall", measureIntervall)
                except:
                    print("Illegal Input")
            # Config LoRaWAN APPKey
            elif ble_config_param == GuiTags.BLE_CONFIG_PARAM.APP_KEY:
                rawdata = self.findChild(QtWidgets.QTextEdit, GuiTags.CONFIG_FIELD_APP_KEY).toPlainText()
                data = [int(rawdata[i:i + 2], 16) for i in range(0, len(rawdata), 2)]
                if len(data) == 16:
                    data.insert(0, GuiTags.BLE_CONFIG_PARAM.APP_KEY.value)
                    asyncio.ensure_future(self.writeChars(GuiTags.WGS_CONFIG_UUID, data), loop=self.loop)
                    print('Der App Key wurde übertragen')
                else:
                    print('Der eingegebene App Key ist nicht zulässig')
            elif ble_config_param == GuiTags.BLE_CONFIG_PARAM.SENSOR_TYPE:
                pass
            elif ble_config_param == GuiTags.BLE_CONFIG_PARAM.DEV_EUI:
                rawdata = self.findChild(QtWidgets.QTextEdit, GuiTags.CONFIG_FIELD_DEVEUI).toPlainText()
                data = [int(rawdata[i:i + 2], 16) for i in range(0, len(rawdata), 2)]
                if len(data) == 8:
                    data.insert(0, GuiTags.BLE_CONFIG_PARAM.DEV_EUI.value)
                    asyncio.ensure_future(self.writeChars(GuiTags.WGS_CONFIG_UUID, data), loop=self.loop)
                    print('Die Dev EUI wurde übertragen')
                else:
                    print('Die eingegebene EUI ist nicht zulässig')

    def startScan(self):
        self.ScanButtonPressed = True
        if (self.findChild(QtWidgets.QRadioButton, GuiTags.CONNECTION_CHOICE_JUST_SCAN).isChecked()):
            asyncio.ensure_future(self.scanAndParse(), loop=self.loop)
        else:
            print()

            asyncio.ensure_future(self.progressBar(), loop=self.loop)
            asyncio.ensure_future(self.startBleScan(), loop=self.loop)

    # self.scanTable.addRowInToTable(row_test)

    async def writeChars(self, uuid, data, disconnect=False):
        await self.bleDevice.client.write_gatt_char(uuid, data)
        if (disconnect):
            await self.bleDevice.client.disconnect()
            self.setConnectionStatusDisconnected()

    def scanner_callback_parse_adv(self, device: BLEDevice, advertisement_data: AdvertisementData):
        allData = advertisement_data.all_data
        if allData == None:
            return
        for i in range(0, len(allData)):
            if len(allData) < i + 4:
                break
            if allData[i] == GuiTags.WGS_ADV_PREAMBLE[0] and allData[i + 1] == GuiTags.WGS_ADV_PREAMBLE[1] and allData[
                i + 2] == GuiTags.WGS_ADV_PREAMBLE[2] and allData[i + 3] == GuiTags.WGS_ADV_PREAMBLE[3]:

                for lpp in wgs_lpp_parser.parse_byte_array(allData[i + 4:]):
                    self.scanAdvParserTable.addRowInToTable([int(time.time()), lpp.channel, lpp.name, lpp.value_f])

    def fillDummyData(self):
        allData = [0x76, 0x64, 0x17, 0x2, 0x0, 0x0, 0x76, 0x85, 1, 103, 0xef, 0x00, 0x0, 0x0, 0x0, 0x0]
        for i in range(0, 4):
            new_row = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
            new_row[0] = convert_int_in_hex_string(allData[0:4])
            new_row[1] = convert_bytes_in_int_lsb(allData[4:], 4)
            wgsRet = wgs_lpp_parser.parse_byte_array(allData[8:])
            for t in wgsRet:
                print(t.name, t.value_f)
            # new_row[2] = allData[8] #Type
            new_row[2] = wgsRet[0].name
            new_row[3] = wgsRet[0].channel
            new_row[4] = wgsRet[0].value_f
            # new_row[3] = allData[9] #Channel
            # new_row[4] = convert_bytes_in_int_lsb(allData[10:],Sensors.get_value_size(Sensors.SENSOR_TYPES(new_row[2])) )
            # print(int_values, " | ",new_row )

            self.eggDataTable.addRowInToTable(new_row)

    async def scanAndParse(self):
        scanner = BleakScanner()
        scanner.register_detection_callback(self.scanner_callback_parse_adv)
        await scanner.start()
        await asyncio.sleep(5.0)
        await scanner.stop()

    async def progressBar(self):
        count = 0
        for i in range(0, 5):
            await asyncio.sleep(int(5))
            count += 19

            self.scanProgressBar.setValue(count)

    async def startBleScan(self):
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
            self.scanTable.addRowInToTable(new_row)

    def startConnect(self):
        asyncio.ensure_future(self.startConnect_(), loop=self.loop)

    async def startConnect_(self):

        macAddr = self.scanTable.item(self.scanTable.currentRow(), 0).text()
        client = BleakClient(macAddr)
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

            self.setConnectionStatusConnected(client)
        except Exception as e:
            self.setConnectionStatusDisconnected()
            self.scanProgressBar.setValue(0)

    def setConnectionStatusConnected(self, client):
        self.bleDevice.client = client
        self.bleDevice.connected = True
        self.connectionLabel.setText("Connected")
        self.connectionLabel.setStyleSheet('color: green')
        if (self.findChild(QtWidgets.QRadioButton, GuiTags.CONNECTION_CHOICE_DATA).isChecked()):
            asyncio.ensure_future(self.waitForData(), loop=self.loop)

    def setConnectionStatusDisconnected(self):
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
        new_row[4] = convert_bytes_in_int_lsb2(int_values[10:],
                                               Sensors.get_value_size(Sensors.SENSOR_TYPES(new_row[2])))
        # print(int_values, " | ",new_row )

        self.eggDataTable.addRowInToTable(new_row)

    async def waitForData(self):
        await self.bleDevice.client.start_notify(GuiTags.WGS_DATA_UUID, self.notification_handler)
        await asyncio.sleep(5.0)
        await self.bleDevice.stop_notify(GuiTags.WGS_DATA_UUID)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)
    window = Ui(loop)
    window.show()
    # app.exec_()
    with loop:
        loop.run_forever()
