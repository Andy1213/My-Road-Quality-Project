# Purpose: parse TCX files generated by MapMyRide and merge with RPi accel data - write to SQLite DB and GeoJSON files
# see   https://pypi.python.org/pypi/python-tcxparser/0.7.1
#       https://pypi.python.org/pypi/geojson/2.3.0
# 2017 10 15 AJL Output to SQL DB
# 2017 10 16 AJL Output GeoJSON example file using dummy road data
# 2017 10 17 AJL Trip elapsed time in seconds written to DB
# 2017 10 18 AJL Interpolated accelarometer data from RPi integrated into GeoJSON file
# 2017 10 19 AJL Adjusted for difference in RPi clock (accel data) and cell phone time (GPS data)

import xml.etree.ElementTree as ET
import sqlite3
import json
import codecs
import platform
from geojson import Feature, Point, FeatureCollection, dumps
from random import *
import csv

# open an interpolated RQM CSV file for input (produced by the RPi)
RQM_data = []
rowcntr = 0
with open('C:\Users\Andy\OneDrive\code\Python\myCode\RoadQualityProject\Data\\RQM_Interpolated.csv', 'rb') as csvfile:
    RQM_file = csv.reader(csvfile, delimiter=',')
    for row in RQM_file:
        if rowcntr > 0:
            RQM_data.append(float(row[1]))
        rowcntr = rowcntr + 1

#print "RQM_data"
#print RQM_data

# open a GeoJSON file for output
fOut = open("C:\Users\Andy\OneDrive\code\Python\myCode\RoadQualityProject\Data\myGeoJSON.js","w")
fOut.write('eqfeed_callback(')
my_datum = []

# the MapMyRaide dataset uses a defult namespace that must prepend searches
defaultnamespace = '{http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2}'
GPStracking = [[0,0,0,0]] # TimeOfDay, LAT, LON, ElapsedTime

#myXML = ET.parse('C:\Users\Andy\OneDrive\code\Python\myCode\RoadQualityProject\Data\Rode 18_77 mi on Baroudeur 20.tcx')
#myXML = ET.parse('C:\Users\Andy\OneDrive\code\Python\myCode\RoadQualityProject\Data\DogWalk.xml')
myXML = ET.parse('C:\Users\Andy\OneDrive\code\Python\myCode\RoadQualityProject\Data\Road_1.tcx')
root = myXML.getroot()
#print len(root)
#print "RootDotTag ", root.tag
#print "RootDotAttrib ", root.attrib

for child in root:
    print "ChildDotTag and ChildDotAttrib" , child.tag, child.attrib

# open an SQLite DB for output
myOS = platform.system()
if (myOS[0:1] == "W"):
    conn = sqlite3.connect('C:\Users\Andy\OneDrive\code\Python\myCode\RoadQualityProject\Data\myRoadDataGPS.sqlite')

cur = conn.cursor()

# empty database of old data
cur.execute('''DELETE FROM GPS_Data WHERE LAT > -1''')

# parse the XML to get time, LAT and LON
for times in myXML.iter(defaultnamespace+'Time'):
    #print times.text
    GPStracking.append([times.text, 0.0, 0.0, 0.0])

icount = 1

for lats in myXML.iter(defaultnamespace+'LatitudeDegrees'):
    #print lats.text
    savept = GPStracking[icount]
    savept[1] = lats.text
    GPStracking[icount] = savept
    icount = icount + 1

icount = 1

# extract the longitude and save it with latitude and time data to the DB and GeoJSON file
for lons in myXML.iter(defaultnamespace+'LongitudeDegrees'):
    #print lons.text
    savept = GPStracking[icount]
    savept[2] = lons.text
    savept[3] = icount * 3
    GPStracking[icount] = savept
    #print GPStracking[icount]
    data_0 = savept[0]
    data_1 = savept[1]
    data_2 = savept[2]
    data_3 = savept[3]
    
    #write to GeoJSON file - arguement order is longitude, latitude
    my_point = Point((float(data_2), float(data_1)))
    
    # generate a bump magnitude (1=smooth road 2=marginal 3=rough) from accelerometer data
    T_lookup = (icount * 3) + 111 # offset lookup for difference in RPi and phone clocks
    if T_lookup < 1:
        T_lookup = 1
    if T_lookup >= len(RQM_data):
        T_lookup = len(RQM_data) - 2
        
    bump_unscal = abs(RQM_data[T_lookup])

    if bump_unscal > 0:
        mag = 1.0
    if bump_unscal > 700:
        mag = 2.0
    if bump_unscal > 1500:
        mag = 3.0
    my_datum.append(Feature(geometry=my_point, properties={"mag": mag}))
    
    #write to SQL file
    cur.execute('''INSERT OR REPLACE INTO GPS_Data
    (GPS_Time,
    LAT,
    LON,
    ElapsedTime)
    VALUES ( ?,
    ?,
    ?,
    ?
     )''', 
    ( data_0,
    data_1,
    data_2,
    data_3
    ))
    icount = icount + 1
    
# write changes to SQL
conn.commit()

# close GeoJSON file
feature_collection = FeatureCollection(my_datum)
fOut.write(dumps(feature_collection))
fOut.write(');')
fOut.close()

# end of script
print("Done!")
