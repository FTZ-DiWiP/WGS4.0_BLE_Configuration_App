from enum import Enum

DATA_TABLE = 'eggDataTable'
CLEAN_DATA_TABLE_BUTTON = 'cleanEggDataTableButton'
SCAN_TABLE = 'scanTable'
SCAN_BUTTON = 'scanButton'
CONNECT_BUTTON = 'connectButton'
CONNECTION_STATUS_LABEL = 'connectionStatusLabel'
SCAN_PROGRESS_BAR = 'scanProgressBar'

SCAN_PARSE_ADV_TABLE = 'scanTableWgsLpp'

DEVICE_NAME = 'WatergridSense Sensor'

CONNECTION_CHOICE_CONFIG = 'choiceConnectionConfig'
CONNECTION_CHOICE_DATA = 'choiceConnectionData'
CONNECTION_CHOICE_JUST_SCAN = 'choiceJustScan'

CONFIG_LIST_APP = 'configListApp'
CONFIG_FIELD_MEASURE_INTERVAL = 'configFieldMeasureTime'
CONFIG_FIELD_DEVEUI = 'configFieldDevEUI'
CONFIG_FIELD_APP_KEY = 'configFieldAppKey'
CONFIG_LIST_SENSORS = 'configListSensors'

STATUS_MQTT_LABEL = 'labelConnectionMQTT'
PUBLISH_MQTT_LABEL = 'publishEggDataTableButton'

# BUTTONS
CONFIG_PROGRAM_BUTTON_APP = 'configProgramButtonApp'
CONFIG_PROGRAM_BUTTON_SENSORS = 'configProgramButtonSensors'
CONFIG_PROGRAM_BUTTON_MEASURE_INTERVAL = 'configProgramButtonMeasureInterval'
CONFIG_PROGRAM_BUTTON_APP_KEY = 'configProgramButtonAppKey'
CONFIG_BUTTON_DEVEUI = 'configButtonDevEUI'
CONFIG_PROGRAM_BUTTON_START = 'configProgramButtonStart'
CONFIG_PROGRAM_BUTTON_STOP = 'configProgramButtonStop'
CONFIG_PROGRAM_BUTTON_RESET = 'configProgramButtonReset'
CONFIG_PROGRAM_BUTTON_TIME = 'configProgramButtonTime'
EXPORT_TO_CSV_BUTTON = "exportToCsvButton"
# MENU
MENU_INTERFACE_MQTT = 'actionMQTTConfig'


class Application(Enum):
    TRUMME = 0
    EGG = 1


class BleConfigParam(Enum):
    MEASURE_INTERVAL = 0x00
    TRANSMIT_INTERVAL = 0x01
    APP_EUI = 0x02
    APP_KEY = 0x03
    SENSOR_TYPE = 0x04
    RESET = 0x05
    START = 0x06
    STOP = 0x07
    TIME = 0x08
    DEV_EUI = 0x09


MAX_LORAWAN_KEY_LEN = 16 * 2

WGS_CONFIG_UUID = "d3a335f8-c3f7-ff46-0f46-284606f8c8f7"
WGS_DATA_UUID = "0441ea4f-b530-4300-f083-bf00e0024100"
WGS_ADV_PREAMBLE = [0x8f, 0xa3, 0xfa, 0x75]
