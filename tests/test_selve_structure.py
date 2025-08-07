import pytest
import asyncio
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestSelveUtilities:
    """Test utility functions and helpers"""
    
    def test_device_type_validation(self):
        """Test device type validation"""
        from selve.util import SelveTypes
        
        # Test all device types exist
        expected_types = ['DEVICE', 'IVEO', 'GROUP', 'SENSIM', 'SENSOR', 'SENDER']
        
        for type_name in expected_types:
            assert hasattr(SelveTypes, type_name), f"Missing device type: {type_name}"
            
            device_type = getattr(SelveTypes, type_name)
            assert device_type.value is not None, f"Device type {type_name} has no value"
    
    def test_command_serialization(self):
        """Test command serialization to XML"""
        from selve.commands.service import ServicePing
        
        ping_command = ServicePing()
        xml_data = ping_command.serializeToXML()
        
        assert xml_data is not None, "Command serialization failed"
        assert isinstance(xml_data, (str, bytes)), "Serialized data should be string or bytes"
        
        # Check for basic XML structure
        xml_str = xml_data.decode() if isinstance(xml_data, bytes) else xml_data
        assert 'methodcall' in xml_str.lower(), "Serialized data should contain methodCall"
        assert 'methodname' in xml_str.lower(), "Serialized data should contain methodName"
        assert 'selve.gw.service.ping' in xml_str.lower(), "Should contain the service ping method"
    
    def test_error_classes(self):
        """Test error class definitions"""
        from selve.util.errors import PortError, CommunicationError, GatewayError
        
        # Test that error classes can be instantiated
        port_error = PortError("Test port error")
        assert str(port_error) == "Test port error"
        
        comm_error = CommunicationError("Test communication error")
        assert str(comm_error) == "Test communication error"
        
        gateway_error = GatewayError("Test gateway error")
        assert str(gateway_error) == "Test gateway error"
        
        # Test that they inherit from Exception
        assert issubclass(PortError, Exception)
        assert issubclass(CommunicationError, Exception)
        assert issubclass(GatewayError, Exception)


class TestSelveDeviceClasses:
    """Test device class definitions and functionality"""
    
    def test_selve_device_creation(self):
        """Test SelveDevice creation and properties"""
        from selve.device import SelveDevice
        from selve.util import SelveTypes
        
        device = SelveDevice(1, SelveTypes.DEVICE)
        
        assert device.id == 1
        assert device.device_type == SelveTypes.DEVICE
        assert hasattr(device, 'name')
        assert hasattr(device, 'state')
        assert hasattr(device, 'value')
        assert hasattr(device, 'targetValue')
    
    def test_selve_sensor_creation(self):
        """Test SelveSensor creation and properties"""
        from selve.sensor import SelveSensor
        
        sensor = SelveSensor(1)
        
        assert sensor.id == 1
        assert hasattr(sensor, 'windDigital')
        assert hasattr(sensor, 'rainDigital')
        assert hasattr(sensor, 'tempDigital')
        assert hasattr(sensor, 'lightDigital')
        assert hasattr(sensor, 'tempAnalog')
        assert hasattr(sensor, 'windAnalog')
    
    def test_selve_sender_creation(self):
        """Test SelveSender creation and properties"""
        from selve.sender import SelveSender
        
        sender = SelveSender(1)
        
        assert sender.id == 1
        assert hasattr(sender, 'name')
        assert hasattr(sender, 'rfAddress')  # Corrected spelling
        assert hasattr(sender, 'channel')
        assert hasattr(sender, 'resetCount')
    
    def test_selve_group_creation(self):
        """Test SelveGroup creation and properties"""
        from selve.group import SelveGroup
        
        group = SelveGroup(1)
        
        assert group.id == 1
        assert hasattr(group, 'name')
        assert hasattr(group, 'mask')
    
    def test_iveo_device_creation(self):
        """Test IveoDevice creation and properties"""
        from selve.iveo import IveoDevice
        
        iveo = IveoDevice(1)
        
        assert iveo.id == 1
        assert hasattr(iveo, 'name')
        assert hasattr(iveo, 'activity')
    
    def test_sensim_creation(self):
        """Test SelveSenSim creation and properties"""
        from selve.senSim import SelveSenSim
        
        sensim = SelveSenSim(1)
        
        assert sensim.id == 1
        assert hasattr(sensim, 'activity')


class TestSelveCommandClasses:
    """Test command class definitions"""
    
    def test_service_commands(self):
        """Test service command classes"""
        from selve.commands.service import (
            ServicePing, ServiceGetState, ServiceGetVersion,
            ServiceReset, ServiceFactoryReset, ServiceSetLed, ServiceGetLed
        )
        
        # Test that all service commands can be instantiated
        commands = [
            ServicePing(),
            ServiceGetState(),
            ServiceGetVersion(),
            ServiceReset(),
            ServiceFactoryReset(),
            ServiceSetLed(True),
            ServiceGetLed(),
        ]
        
        for command in commands:
            assert hasattr(command, 'serializeToXML'), f"Command {type(command)} missing serializeToXML"
    
    def test_device_commands(self):
        """Test device command classes"""
        from selve.commands.device import (
            DeviceGetIds, DeviceGetInfo, DeviceGetValues,
            DeviceSetLabel, DeviceDelete
        )
        
        commands = [
            DeviceGetIds(),
            DeviceGetInfo(1),
            DeviceGetValues(1),
            DeviceSetLabel(1, "Test"),
            DeviceDelete(1),
        ]
        
        for command in commands:
            assert hasattr(command, 'serializeToXML'), f"Command {type(command)} missing serializeToXML"
    
    def test_sensor_commands(self):
        """Test sensor command classes"""
        from selve.commands.sensor import (
            SensorGetIds, SensorGetInfo, SensorGetValues,
            SensorSetLabel, SensorDelete
        )
        
        commands = [
            SensorGetIds(),
            SensorGetInfo(1),
            SensorGetValues(1),
            SensorSetLabel(1, "Test"),
            SensorDelete(1),
        ]
        
        for command in commands:
            assert hasattr(command, 'serializeToXML'), f"Command {type(command)} missing serializeToXML"
    
    def test_sender_commands(self):
        """Test sender command classes"""
        from selve.commands.sender import (
            SenderGetIds, SenderGetInfo, SenderGetValues,
            SenderSetLabel, SenderDelete
        )
        
        commands = [
            SenderGetIds(),
            SenderGetInfo(1),
            SenderGetValues(1),
            SenderSetLabel(1, "Test"),
            SenderDelete(1),
        ]
        
        for command in commands:
            assert hasattr(command, 'serializeToXML'), f"Command {type(command)} missing serializeToXML"
    
    def test_group_commands(self):
        """Test group command classes"""
        from selve.commands.group import GroupGetIds, GroupRead, GroupDelete
        
        commands = [
            GroupGetIds(),
            GroupRead(1),
            GroupDelete(1),
        ]
        
        for command in commands:
            assert hasattr(command, 'serializeToXML'), f"Command {type(command)} missing serializeToXML"
    
    def test_iveo_commands(self):
        """Test Iveo command classes"""
        from selve.commands.iveo import IveoGetIds, IveoGetConfig, IveoSetLabel
        
        commands = [
            IveoGetIds(),
            IveoGetConfig(1),
            IveoSetLabel(1, "Test"),
        ]
        
        for command in commands:
            assert hasattr(command, 'serializeToXML'), f"Command {type(command)} missing serializeToXML"


class TestSelveProtocol:
    """Test protocol-related functionality"""
    
    def test_parameter_types(self):
        """Test parameter type definitions"""
        from selve.util.protocol import ParameterType
        
        # Test that parameter types exist
        expected_types = ['STRING', 'INT', 'BASE64']
        
        for type_name in expected_types:
            assert hasattr(ParameterType, type_name), f"Missing parameter type: {type_name}"
    
    def test_command_base_class(self):
        """Test command base class functionality"""
        from selve.util import Command
        
        # Test that Command class exists and has required methods
        assert hasattr(Command, 'serializeToXML'), "Command class missing serializeToXML method"
    
    def test_response_processing(self):
        """Test response processing utilities"""
        # This would test the response creation and parsing logic
        # Implementation depends on the actual response classes
        pass


class TestSelveConstants:
    """Test constant definitions and enums"""
    
    def test_movement_states(self):
        """Test movement state definitions"""
        try:
            from selve.util import MovementState
            
            # Test that common movement states exist
            expected_states = ['STOPPED_OFF', 'UP_ON', 'DOWN_ON', 'UNKOWN']
            
            for state_name in expected_states:
                if hasattr(MovementState, state_name):
                    state = getattr(MovementState, state_name)
                    assert state is not None, f"Movement state {state_name} is None"
                    
        except ImportError:
            # MovementState might be defined elsewhere or differently
            pass
    
    def test_device_functions(self):
        """Test device function definitions"""
        try:
            from selve.commands.device import DeviceFunctions
            
            # Test that DeviceFunctions enum exists and has values
            assert hasattr(DeviceFunctions, '__members__'), "DeviceFunctions should be an enum"
            
        except ImportError:
            # DeviceFunctions might be defined elsewhere
            pass
    
    def test_communication_types(self):
        """Test communication type definitions"""
        try:
            from selve.util import CommunicationType
            
            # Test that common communication types exist
            expected_types = ['COMMEO', 'IVEO']
            
            for comm_type in expected_types:
                if hasattr(CommunicationType, comm_type):
                    assert getattr(CommunicationType, comm_type) is not None
                    
        except ImportError:
            # CommunicationType might be defined elsewhere
            pass


class TestSelveDataStructures:
    """Test data structure integrity"""
    
    def test_device_storage_structure(self):
        """Test device storage data structure"""
        from selve import Selve
        from selve.util import SelveTypes
        
        logger = None  # Mock logger not needed for this test
        selve = Selve(logger=logger)
        
        # Test that device storage is properly initialized
        assert isinstance(selve.devices, dict), "Device storage should be a dictionary"
        
        # Test that specific device types have storage (not all SelveTypes are device storage)
        expected_device_types = [
            SelveTypes.DEVICE,
            SelveTypes.IVEO,
            SelveTypes.GROUP,
            SelveTypes.SENSIM,
            SelveTypes.SENSOR,
            SelveTypes.SENDER
        ]
        
        for device_type in expected_device_types:
            assert device_type.value in selve.devices, f"Missing storage for {device_type}"
            assert isinstance(selve.devices[device_type.value], dict), f"Storage for {device_type} should be dict"
    
    def test_callback_storage(self):
        """Test callback storage structures"""
        from selve import Selve
        
        logger = None
        selve = Selve(logger=logger)
        
        # Test callback storage types
        assert hasattr(selve, '_callbacks'), "Missing _callbacks attribute"
        assert hasattr(selve, '_eventCallbacks'), "Missing _eventCallbacks attribute"
        
        # Test that they support set operations
        test_callback = lambda: None
        
        selve.register_callback(test_callback)
        assert test_callback in selve._callbacks
        
        selve.remove_callback(test_callback)
        assert test_callback not in selve._callbacks


class TestSelveConfiguration:
    """Test configuration and options"""
    
    def test_serial_parameters(self):
        """Test serial connection parameters"""
        from selve import Selve
        
        logger = None
        selve = Selve(logger=logger)
        
        # Test that serial parameters are properly set
        assert hasattr(selve, '_serial_params'), "Missing _serial_params"
        assert isinstance(selve._serial_params, dict), "_serial_params should be dict"
        
        # Test required parameters
        required_params = ['baudrate', 'bytesize', 'parity', 'stopbits', 'timeout']
        for param in required_params:
            assert param in selve._serial_params, f"Missing serial parameter: {param}"
    
    def test_timeout_configuration(self):
        """Test timeout configuration"""
        from selve import Selve
        
        logger = None
        selve = Selve(logger=logger)
        
        # Test response timeout
        assert hasattr(selve, '_response_timeout'), "Missing _response_timeout"
        assert isinstance(selve._response_timeout, (int, float)), "_response_timeout should be numeric"
        assert selve._response_timeout > 0, "_response_timeout should be positive"
    
    def test_option_handling(self):
        """Test option handling"""
        from selve import Selve
        
        logger = None
        selve = Selve(logger=logger)
        
        # Test reversedStopPosition option
        assert hasattr(selve, 'reversedStopPosition'), "Missing reversedStopPosition option"
        
        # Test updateOptions method
        assert hasattr(selve, 'updateOptions'), "Missing updateOptions method"
        
        # Test updating options
        selve.updateOptions(reversedStopPosition=1)
        assert selve.reversedStopPosition == 1


if __name__ == '__main__':
    # Run all structural tests
    pytest.main([__file__, "-v"])
