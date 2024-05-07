from pymbta3 import Alerts
from pymbta3 import Predictions
from datetime import datetime

current_dateTime = datetime.now()

print(current_dateTime)

keyy = "99352d4263d4425e89446962e66a7cc7"
at = Alerts(key=keyy)
pt = Predictions(key=keyy)
theline = ""

line = input("Line: ")
if line == "red":
    theline = "Red"
    station = "Station.txt"
    codee = "StationCode.txt"
elif line == "orange":
    theline = "Orange"
    station = "StationO.txt"
    codee = "StationCodeO.txt"
elif line == "green":
    pie = input("Branch: ")
    if pie == "b":
        theline = "Green-B"
        station = "StationGB.txt"
        codee = "StationCodeGB.txt"
    elif pie == "c":
        theline = "Green-C"
        station = "StationGC.txt"
        codee = "StationCodeGC.txt"
    elif pie == "d":
        theline = "Green-D"
        station = "StationGD.txt"
        codee = "StationCodeGD.txt"
    elif pie == "e":
        theline = "Green-E"
        station = "StationGE.txt"
        codee = "StationCodeGE.txt"
    else:
        print("error")
        station = "StationG.txt"
        codee = "StationCodeG.txt"
        quit()
elif line == "blue":
    theline = "Blue"
    station = "StationB.txt"
    codee = "StationCodeB.txt"
else:
    print("error")
    exit()

# Open station file for reading
Rmyfile = open(station, "rt")
contents = Rmyfile.read()
x = contents.split()

Rmyfile2 = open(codee, "rt")
contents2 = Rmyfile2.read()
x2 = contents2.split()

p = -1

# Input full name for red line list
dest = input("Lookup Destination: ")
if dest not in contents:
    print("Not Found")
else:
    for i in x:
        p = p + 1
        if i == dest:
            print(p)
# end loop on successful search
            break
# collects code word depending on placement in list
y = x2[p]

alerts = at.get(stop=y)
predictions = pt.get(stop=y, route=[theline])

# Find the short header for the alert
for alert in alerts['data']:
    alertstr = alert['attributes']['short_header']
    print(alertstr)

start1 = 0
start2 = 0
# Find arrival times for prediction
# 0 = outbound 1 = inbound
for prediction in predictions['data']:
    predictionnum = str(prediction['attributes']['arrival_time'])
    predictiondir = str(prediction['attributes']['direction_id'])
    if predictiondir == "0" and start1 == 0:
        print(predictionnum, predictiondir)
        start1 = 1
    if predictiondir == "1" and start2 == 0:
        print(predictionnum, predictiondir)
        start2 = 1

start1 = 0
start2 = 0
