#!/usr/bin/python3
"""
Quickly modified code to log Mikrotik Wireless Wire W60g device data via snmp based on https://github.com/intelroman/snmp_mikrotik/blob/master/mikrotik.py
"""
from pysnmp.carrier.asyncore.dispatch import AsyncoreDispatcher
from pysnmp.carrier.asyncore.dgram import udp
from pyasn1.codec.ber import encoder, decoder
from pysnmp.proto.api import v2c
from time import time

import os
from pprint import pprint as pp

SNMP_HOST = '192.168.88.2'
SNMP_COMMUNITY = 'public'

while(True):
    try:
        date = os.popen("date +%s").read().split('\n')
        t = ((int(date[0])) * 1000000000 - 10000000000)
        hn = os.popen("hostname").read().split('\n')
        data = {}

        # SNMP table header
        headVars = [v2c.ObjectIdentifier((1, 3, 6))]

        # Build PDU
        reqPDU = v2c.GetBulkRequestPDU()
        v2c.apiBulkPDU.setDefaults(reqPDU)
        v2c.apiBulkPDU.setNonRepeaters(reqPDU, 0)
        v2c.apiBulkPDU.setMaxRepetitions(reqPDU, 25)
        v2c.apiBulkPDU.setVarBinds(reqPDU, [(x, v2c.null) for x in headVars])

        # Build message
        reqMsg = v2c.Message()
        v2c.apiMessage.setDefaults(reqMsg)
        v2c.apiMessage.setCommunity(reqMsg, SNMP_COMMUNITY)
        v2c.apiMessage.setPDU(reqMsg, reqPDU)

        startedAt = time()


        def cbTimerFun(timeNow):
            if timeNow - startedAt > 3:
                raise Exception("Request timed out")


        # noinspection PyUnusedLocal
        def cbRecvFun(transportDispatcher, transportDomain, transportAddress,
                    wholeMsg, reqPDU=reqPDU, headVars=headVars):
            while wholeMsg:
                rspMsg, wholeMsg = decoder.decode(wholeMsg, asn1Spec=v2c.Message())

                rspPDU = v2c.apiMessage.getPDU(rspMsg)

                # Match response to request
                if v2c.apiBulkPDU.getRequestID(reqPDU) == v2c.apiBulkPDU.getRequestID(rspPDU):
                    # Format var-binds table
                    varBindTable = v2c.apiBulkPDU.getVarBindTable(reqPDU, rspPDU)

                    # Check for SNMP errors reported
                    errorStatus = v2c.apiBulkPDU.getErrorStatus(rspPDU)
                    if errorStatus and errorStatus != 2:
                        errorIndex = v2c.apiBulkPDU.getErrorIndex(rspPDU)
                        print('%s at %s' % (errorStatus.prettyPrint(),
                                            errorIndex and varBindTable[int(errorIndex) - 1] or '?'))
                        transportDispatcher.jobFinished(1)
                        break

                    # Report SNMP table
                    for tableRow in varBindTable:
                        for name, val in tableRow:
        #                   print('from: %s, %s = %s' % (
        #                        transportAddress, name.prettyPrint(), val.prettyPrint()
        #                    )
        #                          )
                            data.update({ (name.prettyPrint()) : (val.prettyPrint())})

                    # Stop on EOM
                    for oid, val in varBindTable[-1]:
                        if not isinstance(val, v2c.Null):
                            break
                    else:
                        transportDispatcher.jobFinished(1)

                    # Generate request for next row
                    v2c.apiBulkPDU.setVarBinds(
                        reqPDU, [(x, v2c.null) for x, y in varBindTable[-1]]
                    )
                    v2c.apiBulkPDU.setRequestID(reqPDU, v2c.getNextRequestID())
                    transportDispatcher.sendMessage(
                        encoder.encode(reqMsg), transportDomain, transportAddress
                    )
                    global startedAt
                    if time() - startedAt > 3:
                        raise Exception('Request timed out')
                    startedAt = time()
            return wholeMsg


        transportDispatcher = AsyncoreDispatcher()

        transportDispatcher.registerRecvCbFun(cbRecvFun)
        transportDispatcher.registerTimerCbFun(cbTimerFun)

        transportDispatcher.registerTransport(
            udp.domainName, udp.UdpSocketTransport().openClientMode()
        )
        transportDispatcher.sendMessage(
            encoder.encode(reqMsg), udp.domainName, (SNMP_HOST, 161)
        )
        transportDispatcher.jobStarted(1)

        # Dispatcher will finish as job#1 counter reaches zero
        transportDispatcher.runDispatcher()

        transportDispatcher.closeDispatcher()

        ifindex = []
        if_stats = {}
        for i in data.keys():
            if '1.3.6.1.4.1.14988.1.1.1.8.1.2.' in i:
                #print(i)
                ifindex.append(i.split('.')[-1])

        #print(ifindex)

        for i in ifindex:
            if_stats.update({data["1.3.6.1.4.1.14988.1.1.1.8.1.2.%s" % (i)]:{
                                            "mode": data['1.3.6.1.4.1.14988.1.1.1.8.1.2.%s' % (i)],
                                            "ssid": data['1.3.6.1.4.1.14988.1.1.1.8.1.3.%s' % (i)],
                                            "con": data['1.3.6.1.4.1.14988.1.1.1.8.1.4.%s' % (i)],
                                            "mac": data['1.3.6.1.4.1.14988.1.1.1.8.1.5.%s' % (i)],
                                            "freq": data['1.3.6.1.4.1.14988.1.1.1.8.1.6.%s' % (i)],
                                            "mcs": data['1.3.6.1.4.1.14988.1.1.1.8.1.7.%s' % (i)],
                                            "siq": data['1.3.6.1.4.1.14988.1.1.1.8.1.8.%s' % (i)],
                                            "txsec": data['1.3.6.1.4.1.14988.1.1.1.8.1.9.%s' % (i)],
                                            "sector": data['1.3.6.1.4.1.14988.1.1.1.8.1.11.%s' % (i)],
                                            "rssi": data['1.3.6.1.4.1.14988.1.1.1.8.1.12.%s' % (i)],
                                            "rate": data['1.3.6.1.4.1.14988.1.1.1.8.1.13.%s' % (i)],
                                            "devName": data['1.3.6.1.2.1.1.5.0']
                                            }
                                            })

        influx_int = []
        for i in if_stats.keys():
            data1={
                                "measurement": "snmp",
                                "tags": {
                                        "devName": if_stats[i]['devName']
                                        },
                                "time": t,
                                "fields": {
                                        "mode": if_stats[i]['mode'],
                                        "ssid": if_stats[i]['ssid'],
                                        "con": if_stats[i]['con'],
                                        "mac": if_stats[i]['mac'],
                                        "freq": if_stats[i]['freq'],
                                        "mcs": if_stats[i]['mcs'],
                                        "txsec": if_stats[i]['txsec'],
                                        "sector": if_stats[i]['sector'],
                                        "rssi": if_stats[i]['rssi'],
                                        "rate": if_stats[i]['rate']
                                        

                                        }
                                }
        print(data1)                        


        date = os.popen("date +%s").read().split('\n')
        t = ((int(date[0])) * 1000000000 - 10000000000)
        hn = os.popen("hostname").read().split('\n')
        data = {}

        # SNMP table header
        headVars = [v2c.ObjectIdentifier((1, 3, 6))]

        # Build PDU
        reqPDU = v2c.GetBulkRequestPDU()
        v2c.apiBulkPDU.setDefaults(reqPDU)
        v2c.apiBulkPDU.setNonRepeaters(reqPDU, 0)
        v2c.apiBulkPDU.setMaxRepetitions(reqPDU, 25)
        v2c.apiBulkPDU.setVarBinds(reqPDU, [(x, v2c.null) for x in headVars])

        # Build message
        reqMsg = v2c.Message()
        v2c.apiMessage.setDefaults(reqMsg)
        v2c.apiMessage.setCommunity(reqMsg, SNMP_COMMUNITY)
        v2c.apiMessage.setPDU(reqMsg, reqPDU)

        startedAt = time()


        def cbTimerFun(timeNow):
            if timeNow - startedAt > 3:
                raise Exception("Request timed out")


        # noinspection PyUnusedLocal
        def cbRecvFun(transportDispatcher, transportDomain, transportAddress,
                    wholeMsg, reqPDU=reqPDU, headVars=headVars):
            while wholeMsg:
                rspMsg, wholeMsg = decoder.decode(wholeMsg, asn1Spec=v2c.Message())

                rspPDU = v2c.apiMessage.getPDU(rspMsg)

                # Match response to request
                if v2c.apiBulkPDU.getRequestID(reqPDU) == v2c.apiBulkPDU.getRequestID(rspPDU):
                    # Format var-binds table
                    varBindTable = v2c.apiBulkPDU.getVarBindTable(reqPDU, rspPDU)

                    # Check for SNMP errors reported
                    errorStatus = v2c.apiBulkPDU.getErrorStatus(rspPDU)
                    if errorStatus and errorStatus != 2:
                        errorIndex = v2c.apiBulkPDU.getErrorIndex(rspPDU)
                        print('%s at %s' % (errorStatus.prettyPrint(),
                                            errorIndex and varBindTable[int(errorIndex) - 1] or '?'))
                        transportDispatcher.jobFinished(1)
                        break

                    # Report SNMP table
                    for tableRow in varBindTable:
                        for name, val in tableRow:
        #                   print('from: %s, %s = %s' % (
        #                        transportAddress, name.prettyPrint(), val.prettyPrint()
        #                    )
        #                          )
                            data.update({ (name.prettyPrint()) : (val.prettyPrint())})

                    # Stop on EOM
                    for oid, val in varBindTable[-1]:
                        if not isinstance(val, v2c.Null):
                            break
                    else:
                        transportDispatcher.jobFinished(1)

                    # Generate request for next row
                    v2c.apiBulkPDU.setVarBinds(
                        reqPDU, [(x, v2c.null) for x, y in varBindTable[-1]]
                    )
                    v2c.apiBulkPDU.setRequestID(reqPDU, v2c.getNextRequestID())
                    transportDispatcher.sendMessage(
                        encoder.encode(reqMsg), transportDomain, transportAddress
                    )
                    global startedAt
                    if time() - startedAt > 3:
                        raise Exception('Request timed out')
                    startedAt = time()
            return wholeMsg


        transportDispatcher = AsyncoreDispatcher()

        transportDispatcher.registerRecvCbFun(cbRecvFun)
        transportDispatcher.registerTimerCbFun(cbTimerFun)

        transportDispatcher.registerTransport(
            udp.domainName, udp.UdpSocketTransport().openClientMode()
        )
        transportDispatcher.sendMessage(
            encoder.encode(reqMsg), udp.domainName, (SNMP_HOST, 161)
        )
        transportDispatcher.jobStarted(1)

        # Dispatcher will finish as job#1 counter reaches zero
        transportDispatcher.runDispatcher()

        transportDispatcher.closeDispatcher()

        ifindex = []
        if_stats = {}
        for i in data.keys():
            if '1.3.6.1.4.1.14988.1.1.1.9.1.2.' in i:
                #print(i)
                ifindex.append(i.split('.')[-1])

        #print(ifindex)

        for i in ifindex:
            if_stats.update({data["1.3.6.1.4.1.14988.1.1.1.9.1.2.%s" % (i)]:{
                                            "status": data['1.3.6.1.4.1.14988.1.1.1.9.1.2.%s' % (i)],
                                            "mac": data['1.3.6.1.4.1.14988.1.1.1.9.1.3.%s' % (i)],
                                            "mcs": data['1.3.6.1.4.1.14988.1.1.1.9.1.4.%s' % (i)],
                                            "siq": data['1.3.6.1.4.1.14988.1.1.1.9.1.5.%s' % (i)],
                                            "txsec": data['1.3.6.1.4.1.14988.1.1.1.9.1.6.%s' % (i)],
                                            "rate": data['1.3.6.1.4.1.14988.1.1.1.9.1.8.%s' % (i)],
                                            "rssi": data['1.3.6.1.4.1.14988.1.1.1.9.1.9.%s' % (i)],
                                            "distance": data['1.3.6.1.4.1.14988.1.1.1.9.1.10.%s' % (i)],
                                            "devName": data['1.3.6.1.2.1.1.5.0']
                                            }
                                            })

        influx_int = []
        for i in if_stats.keys():
            data2={
                                "measurement": "snmp",
                                "tags": {
                                        "devName": if_stats[i]['devName']
                                        },
                                "time": t,
                                "fields": {
                                        "status": if_stats[i]['status'],
                                        "mac": if_stats[i]['mac'],
                                        "mcs": if_stats[i]['mcs'],
                                        "siq": if_stats[i]['siq'],
                                        "txsec": if_stats[i]['txsec'],
                                        "rate": if_stats[i]['rate'],
                                        "rssi": if_stats[i]['rssi'],
                                        "distance": if_stats[i]['distance']
                                        

                                        }
                                }
        print(data2)
                                


    except:
        print("sth failed")

    with open("log.json", "a") as f: 
        f.write(str(data1)+"\n")
        f.write(str(data2)+"\n")