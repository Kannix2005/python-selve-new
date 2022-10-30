import logging
import sys
import asyncio
import threading

import selve


## In HA this would be loop = self.hass.loop
loop = asyncio.new_event_loop()
portname = 'COM4'

logger = logging.getLogger("Logger")
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


selve = selve.Selve(portname, loop, develop=False, discover=False, logger=logger)



#try:
#    loop.run_until_complete()
#except KeyboardInterrupt:
#    loop.close()

threading.Thread(target=loop.run_forever, args=())

selve.pingGateway()
#selve.resetGateway()
selve.discover()


#selve.moveDeviceDown(selve.devices['device'][1])
selve.moveGroupUp(selve.devices['group'][1])

loop.run_forever()