# Purpose: Make road quality measurements
#
# 2017 09 07 AJL Created file from copy of RQP_V0_1.py
#                Bar graph is now centered on 1 g
# 2017 09 12 AJL Logging and program exit can be done from a switch using GPIO
# 2017 09 16 AJL Logging measurements in JSON format to file
#                Now calcualting and storing difference between raw and filtered z accel measurements
#                Periodic measurments as well as high g trigger added
#                
# BOM
# ==============================================================
# Raspberry Pi Zero W
# Acrobotic SSD1306 128x64 pixels Blue/Yellow OLED Display
#   see http://ssd1306.readthedocs.io/en/latest/python-usage.html
#   also https://github.com/rm-hull/luma.oled/tree/1.5.0/examples
# LSM303D Accelerometer
#   see https://forum.pololu.com/t/lsm303d-raspberry-pi-driver/7698
# ==============================================================

import time
import RPi.GPIO as GPIO
from oled.serial import i2c
from oled.device import ssd1306, ssd1331, sh1106
from oled.render import canvas

    
# **************************************************************************
#Driver for the LSM303D accelerometer and magnetometer/compass
#First follow the procedure to enable I2C on R-Pi.
#1. Add the lines "ic2-bcm2708" and "i2c-dev" to the file /etc/modules
#2. Comment out the line "blacklist ic2-bcm2708" (with a #) in the file /etc/modprobe.d/raspi-blacklist.conf
#3. Install I2C utility (including smbus) with the command "apt-get install python-smbus i2c-tools"
#4. Connect the I2C device and detect it using the command "i2cdetect -y 1".  It should show up as 1D or 1E (here the variable LSM is set to 1D).
#Driver by Fayetteville Free Library Robotics Group

def twos_comp_combine(msb, lsb):
    twos_comp = 256*msb + lsb
    if twos_comp >= 32768:
        return twos_comp - 65536
    else:
        return twos_comp
            
def LSM303D_z():
    from smbus import SMBus

    busNum = 1
    b = SMBus(busNum)
        
    LSM = 0x1d
    LSM_WHOAMI = 0b1001001 #Device self-id
    
    #Control register addresses -- from LSM303D datasheet
    CTRL_0 = 0x1F #General settings
    CTRL_1 = 0x20 #Turns on accelerometer and configures data rate
    CTRL_2 = 0x21 #Self test accelerometer, anti-aliasing accel filter
    CTRL_3 = 0x22 #Interrupts
    CTRL_4 = 0x23 #Interrupts
    CTRL_5 = 0x24 #Turns on temperature sensor
    CTRL_6 = 0x25 #Magnetic resolution selection, data rate config
    CTRL_7 = 0x26 #Turns on magnetometer and adjusts mode
    #Registers holding twos-complemented MSB and LSB of magnetometer readings -- from LSM303D datasheet
    MAG_X_LSB = 0x08 # x
    MAG_X_MSB = 0x09
    MAG_Y_LSB = 0x0A # y
    MAG_Y_MSB = 0x0B
    MAG_Z_LSB = 0x0C # z
    MAG_Z_MSB = 0x0D
    #Registers holding twos-complemented MSB and LSB of magnetometer readings -- from LSM303D datasheet
    ACC_X_LSB = 0x28 # x
    ACC_X_MSB = 0x29
    ACC_Y_LSB = 0x2A # y
    ACC_Y_MSB = 0x2B
    ACC_Z_LSB = 0x2C # z
    ACC_Z_MSB = 0x2D
    #Registers holding 12-bit right justified, twos-complemented temperature data -- from LSM303D datasheet
    TEMP_MSB = 0x05
    TEMP_LSB = 0x06
    if b.read_byte_data(LSM, 0x0f) == LSM_WHOAMI:
        LSM303D_init = 1
        #print('LSM303D detected successfully.')
    else:
        print('No LSM303D detected on bus '+str(busNum)+'.')

        
    b.write_byte_data(LSM, CTRL_1, 0b1010111) # enable accelerometer, 50 hz sampling
    b.write_byte_data(LSM, CTRL_2, 0x00) #set +/- 2g full scale
    b.write_byte_data(LSM, CTRL_5, 0b01100100) #high resolution mode, thermometer off, 6.25hz ODR
    b.write_byte_data(LSM, CTRL_6, 0b00100000) # set +/- 4 gauss full scale
    b.write_byte_data(LSM, CTRL_7, 0x00) #get magnetometer out of low power mode
    LSM303D_init = 1
   # end of initialization

    #accx = twos_comp_combine(b.read_byte_data(LSM, ACC_X_MSB), b.read_byte_data(LSM, ACC_X_LSB))
    #accy = twos_comp_combine(b.read_byte_data(LSM, ACC_Y_MSB), b.read_byte_data(LSM, ACC_Y_LSB))
    accz = twos_comp_combine(b.read_byte_data(LSM, ACC_Z_MSB), b.read_byte_data(LSM, ACC_Z_LSB))
    # print(accz)
    return accz

def NowSQL():
    # Purpose: create a SQL compatible date format (YYYY-MM-DDTHH:MM:SS)
    # 2017 02 04 AJL Created file
    # 2017 02 10 AJL Corrected error where single digit dates were not having hyphens added
    # 2017 09 16 AJL substituted undersoreds for colons in time string because of JSON parsing error
    
    import time
    
    # Python date format
    PyTime = time.localtime()

    # build the date string in SQL format (YYYY-MM-DDTHH:MM:SS)
    sYear = str(PyTime.tm_year)

    sMonth = str(PyTime.tm_mon)
    if (PyTime.tm_mon < 10):
        sMonth = "0" + sMonth

    sDay = str(PyTime.tm_mday)
    if (PyTime.tm_mday < 10):
        sDay = "0" + sDay
        
    sHour = str(PyTime.tm_hour)
    if (PyTime.tm_hour < 10):
        sHour = "0" + sHour

    sMinute = str(PyTime.tm_min) 
    if (PyTime.tm_min < 10):
        sMinute = "0" + sMinute
        
    sSecond = str(PyTime.tm_sec)
    if (PyTime.tm_sec < 10):
        sSecond = "0" + sSecond
            
    strSQL_date = sYear + "-" + sMonth + "-" + sDay + "T" + str(sHour) + "_" + str(sMinute) + "_" + str(sSecond)

    return strSQL_date


def Date2FileName():
    # Purpose: create file name prefix in the format (YYYYMMDDTHHMMSS)
    # 2017 09 16 AJL Created file
        
    import time
    
    # Python date format
    PyTime = time.localtime()

    # build the date string in SQL format (YYYY-MM-DDTHH:MM:SS)
    sYear = str(PyTime.tm_year)

    sMonth = str(PyTime.tm_mon)
    if (PyTime.tm_mon < 10):
        sMonth = "0" + sMonth

    sDay = str(PyTime.tm_mday)
    if (PyTime.tm_mday < 10):
        sDay = "0" + sDay
        
    sHour = str(PyTime.tm_hour)
    if (PyTime.tm_hour < 10):
        sHour = "0" + sHour

    sMinute = str(PyTime.tm_min) 
    if (PyTime.tm_min < 10):
        sMinute = "0" + sMinute
        
    sSecond = str(PyTime.tm_sec)
    if (PyTime.tm_sec < 10):
        sSecond = "0" + sSecond
            
    TheFileName = sYear + sMonth + sDay + str(sHour) + str(sMinute) + str(sSecond)

    return TheFileName

# ********************************************************************* main()
# initialize I2C interface
serial = i2c(port=1, address=0x3C)

# Acrobotic SSD1306 128x64 pixels Blue/Yellow Font is 6 x 11
device = ssd1306(serial,width=128, height=64, rotate=0)

# setup GPIO using BCM numbering
GPIO.setmode(GPIO.BCM)

# Pin assignments
logPin = 26 # start logging to file
sbyPin = 19 # standby
hltPin = 13 # exit program

# all logging modes will be selected when HIGH
GPIO.setup(logPin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(sbyPin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(hltPin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

# init logging parameters
FLTconst = 0.80
FLT = 17800.00

Logging = 0 # default logging to STANDBY
LoggingMode = "Standby"
LogReason = "Periodic"
DataSource = "LenhartTruck"
LastLog = time.time()
LogInterval = 15 # seconds
MaxDIF = 200 # unscaled reading
LogNow = 0
nPoints = 0

# screen positions - calculate a 1 pixel high horizontal bar and offset to get width
xLabel = 1
xData = 28
LowerLeft = 0
LowerRight = 128

# open file for logging measurements
ThePath = "/home/pi/Documents/python/data/"
FileName = Date2FileName()
FileToOpen = ThePath + FileName + ".csv"
print("Outputfile: ",FileToOpen)
fOut = open(FileToOpen,"w")
 
for iReadings in range(10000):

    # read switch and set mode
    if GPIO.input(logPin):
        Logging = 1
        LoggingMode = "Logging"
        
    if GPIO.input(sbyPin):
        Logging = 0
        LoggingMode = "Standby"

    if GPIO.input(hltPin):
        Logging = 0
        # close the output file
        fOut.close()
        GPIO.cleanup() # cleanup all GPIO
        print("Shutting Down")
        exit()   
            
    with canvas(device) as draw:
        txtSize = draw.textsize('W')
        RQM = LSM303D_z()
        sRQM = str(RQM * 1.0)[0:7]
        FLT = FLT * FLTconst + RQM * (1.0 - FLTconst)
        sFLT = str(FLT)[0:7]
        DIF = RQM - FLT
        sDIF = str(DIF)[0:7]
        hBarLength = RQM / 320
        sLat = "42.4606"
        sLon = "83.1346"

        # determine if we need to log a point - time based
        if  time.time() - LastLog > LogInterval:
            LastLog = time.time()
            LogNow = 1
            LogReason = "Periodic"

        # determine if we need to log a point - we hit a bump
        if  DIF > MaxDIF:
            LastLog = time.time()
            LogNow = 1
            LogReason = "Bump"
        
        # Concatentate measurements into a JSON string
        data0=NowSQL()
        data1=DataSource
        data2=sRQM
        data3=sFLT
        data4 =sDIF
        data5 =sLat
        data6 =sLon
        data7 = LogReason
        
        data_all =  "{@TimeStamp@: @%s@, @DataSource@:@%s@, @RQM@: @%s@, @FLT@: @%s@, @DIF@: @%s@, @LAT@: @%s@, @LON@: @%s@, @Reason@: @%s@}" % (data0, data1, data2, data3, data4, data5, data6, data7)
        data_all = data_all.replace("@",'"')

        #write to file
        if Logging == 1 and LogNow == 1:
            fOut.write(data_all)
            fOut.write("\n")
            nPoints = nPoints + 1

        # calculate length of horizontal bar on OLED display
        # for positive g's
        if  0 < RQM:
            LowerLeft = 64
            LowerRight = 64 + 0.001793734 * RQM
        # for negative g's
        if RQM < 0:
            LowerLeft = 64 + 0.001793734 * RQM
            LowerRight = 64
            
        print("Acceleration in Z:", sRQM, " LowerLeft ", LowerLeft, " LowerRight ",LowerRight )
        print("GPIO 13 ", GPIO.input(hltPin), "GPIO 19 ", GPIO.input(sbyPin), "GPIO 26 ", GPIO.input(logPin))
        
        # draw.text (xPixels, yPixels) font is 6 x 11
        draw.text((xLabel, 0), "Road Quality Project", fill="white")
        LogMessage = LoggingMode + " " + str(nPoints) + " Pts"
        draw.text((xLabel, 14), LogMessage , fill="white")
        
        draw.text((xLabel,22), "RAW", fill="white")
        draw.text((xData, 22), sRQM, fill="white")
        
        draw.text((xLabel,30), "FLT", fill="white")
        draw.text((xData, 30), sFLT, fill="white")

        draw.text((xLabel,38), "LAT", fill="white")
        draw.text((xData, 38), sLat, fill="white")

        draw.text((xLabel,46), "LON", fill="white")
        draw.text((xData, 46), sLon, fill="white")

        draw.rectangle((LowerLeft, 63, LowerRight, 56), fill="white")

        # reset the log point flag
        LogNow = 0
        LogReason = "Periodic"
        time.sleep(0.1)

# timeout
print("Font size ", txtSize)
fOut.close()
GPIO.cleanup() # cleanup all GPIO
print("Max Time Reached")
exit()
