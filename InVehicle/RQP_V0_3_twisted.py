# Purpose: Make road quality measurmetns
# 2017 09 07 AJL Created file from copy of RQP_V0_1.py
#                Bar graph is now centered on 1 g
# 2017 09 12 AJL Logging and program exit can be done from a switch using GPIO
# BOM
# ==============================================================
# Raspberry Pi Zero W
# Acrobotic SSD1306 128x64 pixels Blue/Yellow OLED Display
#   see http://ssd1306.readthedocs.io/en/latest/python-usage.html
#   also https://github.com/rm-hull/luma.oled/tree/1.5.0/examples
# LSM303D Accelerometer
#   see https://forum.pololu.com/t/lsm303d-raspberry-pi-driver/7698

import time
import RPi.GPIO as GPIO
from oled.serial import i2c
from oled.device import ssd1306, ssd1331, sh1106
from oled.render import canvas
from twisted.internet import task
from twisted.internet import reactor

def runEverySecond():
    print("a twisted second has passed")
    
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

# ********************************************************************* main()
# initialize I2C interface
serial = i2c(port=1, address=0x3C)

# Acrbotic SSD1306 128x64 pixels Blue/Yellow Font is 6 x 11
device = ssd1306(serial,width=128, height=64, rotate=0)

# setup GPIO using Board numbering
GPIO.setmode(GPIO.BCM)

# Pin assignments
logPin = 26 # start logging to file
sbyPin = 19 # standby
hltPin = 13 # exit program

GPIO.setup(logPin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(sbyPin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(hltPin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

# open file for logging measurements
fOut = open("/home/pi/Documents/python/data/RQM.csv","w")
Logging = 0 # default to no logging
LoggingMode = "Undefined"

# twisted schedler
l = task.LoopingCall(runEverySecond)
l.start(1.0) # call every second
reactor.run()

# screen positions - calculate a 1 pixel high horizontal bar and offset to get width
xLabel = 1
xData = 28
LowerLeft = 0
LowerRight = 128
 
for iReadings in range(1000):

    # read switch and set mode
    if GPIO.input(logPin):
        Logging = 1
        LoggingMode = "Logging"
        
    if GPIO.input(sbyPin):
        Logging = 0
        LoggingMode = "Standby"

    if GPIO.input(hltPin):
        Logging = 0
        # twisted schedler
        l.stop()
        # close the output file
        fOut.close()
        GPIO.cleanup() # cleanup all GPIO
        print("Shutting Down")
        exit()   
            
    with canvas(device) as draw:
        txtSize = draw.textsize('W')
        RQM = LSM303D_z()
        sRQM = str(RQM)
        hBarLength = RQM / 320
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
        draw.text((xLabel, 14), LoggingMode, fill="white")
        
        draw.text((xLabel,22), "RAW", fill="white")
        draw.text((xData, 22), sRQM, fill="white")
        
        draw.text((xLabel,30), "FLT", fill="white")
        draw.text((xData, 30), "???.???", fill="white")

        draw.text((xLabel,38), "LAT", fill="white")
        draw.text((xData, 38), "???.???", fill="white")

        draw.text((xLabel,46), "LON", fill="white")
        draw.text((xData, 46), "???.???", fill="white")

        #draw.rectangle((xLabel, 60, hBarLength, xLabel + txtSize[1]), fill="white")
        draw.rectangle((LowerLeft, 63, LowerRight, 52), fill="white")
        
        time.sleep(0.1)

print("Font size ", txtSize)
exit()
