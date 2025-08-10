import unittest
from unittest.mock import MagicMock, patch
from selve.commands.service import (
    ServicePing, ServiceGetState, ServiceGetVersion,
    ServiceReset, ServiceFactoryReset, ServiceSetLed, ServiceGetLed,
    ServicePingResponse, ServiceGetStateResponse, ServiceGetVersionResponse
)
from selve.util.protocol import ParameterType


class TestServiceCommands(unittest.TestCase):

    def test_service_ping_command(self):
        """Test creation of a ping command."""
        cmd = ServicePing()
        self.assertEqual(cmd.method_name, "selve.GW.service.ping")
        self.assertEqual(cmd.parameters, [])
    
    def test_service_get_state_command(self):
        """Test creation of a get state command."""
        cmd = ServiceGetState()
        self.assertEqual(cmd.method_name, "selve.GW.service.getState")
        self.assertEqual(cmd.parameters, [])
    
    def test_service_get_version_command(self):
        """Test creation of a get version command."""
        cmd = ServiceGetVersion()
        self.assertEqual(cmd.method_name, "selve.GW.service.getVersion")
        self.assertEqual(cmd.parameters, [])
    
    def test_service_reset_command(self):
        """Test creation of a reset command."""
        cmd = ServiceReset()
        self.assertEqual(cmd.method_name, "selve.GW.service.reset")
        self.assertEqual(cmd.parameters, [])
    
    def test_service_factory_reset_command(self):
        """Test creation of a factory reset command."""
        cmd = ServiceFactoryReset()
        self.assertEqual(cmd.method_name, "selve.GW.service.factoryReset")
        self.assertEqual(cmd.parameters, [])
    
    def test_service_set_led_command(self):
        """Test creation of a set LED command with different values."""
        # Test with LED on
        cmd_on = ServiceSetLed(True)
        self.assertEqual(cmd_on.method_name, "selve.GW.service.setLED")
        self.assertEqual(cmd_on.parameters, [(ParameterType.INT, 1)])
        
        # Test with LED off
        cmd_off = ServiceSetLed(False)
        self.assertEqual(cmd_off.method_name, "selve.GW.service.setLED")
        self.assertEqual(cmd_off.parameters, [(ParameterType.INT, 0)])
    
    def test_service_get_led_command(self):
        """Test creation of a get LED command."""
        cmd = ServiceGetLed()
        self.assertEqual(cmd.method_name, "selve.GW.service.getLED")
        self.assertEqual(cmd.parameters, [])
    
    def test_service_ping_response(self):
        """Test parsing a ping response."""
        response = ServicePingResponse("selve.GW.service.ping", [])
        self.assertEqual(response.name, "selve.GW.service.ping")
    
    def test_service_get_state_response(self):
        """Test parsing a get state response."""
        response = ServiceGetStateResponse("selve.GW.service.getState", [(ParameterType.INT, "2")])
        self.assertEqual(response.name, "selve.GW.service.getState")
        self.assertEqual(response.state, "2")
    
    def test_service_get_version_response(self):
        """Test parsing a get version response."""
        response = ServiceGetVersionResponse("selve.GW.service.getVersion", 
                                            [(ParameterType.STRING, "123456"), 
                                             (ParameterType.INT, 1), 
                                             (ParameterType.INT, 2), 
                                             (ParameterType.INT, 3), 
                                             (ParameterType.INT, 4), 
                                             (ParameterType.INT, 5), 
                                             (ParameterType.INT, 6)])
        self.assertEqual(response.name, "selve.GW.service.getVersion")
        self.assertEqual(response.serial, "123456")
        self.assertEqual(response.version, "1.2.3.6")


if __name__ == "__main__":
    unittest.main()
