import logging
import sys
import asyncio
import selve
from selve.util.commandFactory import Command


## In HA this would be loop = self.hass.loop
loop = asyncio.new_event_loop()
portname = 'COM8'
selve = selve.Selve(portname, loop, develop=True)

selve._LOGGER.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
selve._LOGGER.addHandler(handler)

#try:
#    loop.run_until_complete()
#except KeyboardInterrupt:
#    loop.close()


loop.run_forever()