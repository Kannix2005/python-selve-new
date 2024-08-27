import logging
import sys
import asyncio
import threading

import selve


## In HA this would be loop = self.hass.loop
loop = asyncio.new_event_loop()
portname = None

logger = logging.getLogger("Logger")
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


selve = selve.Selve(portname, develop=True, discover=False, logger=logger, loop=loop)
loop.run_until_complete(selve.setup())

loop.run_until_complete(selve.discover())

loop.run_until_complete(selve.setEvents(1,1,1,1,1))
loop.run_until_complete(selve.getEvents())

#try:
#    loop.run_until_complete()
#except KeyboardInterrupt:
#    loop.close()

#threading.Thread(target=loop.run_forever, args=())

#loop.run_until_complete(selve.pingGateway())
#selve.resetGateway()
#loop.run_until_complete(selve.discover())

#print("Test")

#selve.moveDeviceDown(selve.devices['device'][1])
#selve.moveGroupUp(selve.devices['group'][1])

loop.run_forever()