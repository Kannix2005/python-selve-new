import unittest
from unittest.mock import MagicMock, patch
import asyncio

# Import utility classes and protocols
from selve.util.errors import GatewayError, PortError
from selve.util.protocol import *
from selve.util.protocol import (
    DeviceType, SelveTypes, DeviceState, MovementState, 
    CommunicationType, SenSimCommandType, DriveCommandCommeo,
    DeviceCommandType, DriveCommandIveo, ParameterType,
    ScanState, TeachState, CommandResultState, ServiceState,
    SensorState, RepeaterState, LEDMode, Forwarding,
    DutyMode, DayMode, DeviceFunctions, LogType, DeviceClass,
    windDigital, rainDigital, tempDigital, lightDigital, senderEvents
)


class TestSelveUtilityClasses(unittest.TestCase):
    """Tests to improve coverage for utility classes and enums."""

    def test_gateway_error(self):
        """Test GatewayError creation and properties."""
        # Test with message only
        exception = GatewayError("Test error")
        self.assertEqual(str(exception), "Test error")
        
        # Test with message and cause
        cause = ValueError("Root cause")
        exception_with_cause = GatewayError("Test error with cause")
        self.assertEqual(str(exception_with_cause), "Test error with cause")

    def test_port_error(self):
        """Test PortError creation."""
        port_exception = PortError("Port error occurred")
        self.assertEqual(str(port_exception), "Port error occurred")
        self.assertIsInstance(port_exception, Exception)

    def test_device_type_enum(self):
        """Test DeviceType enum values."""
        self.assertEqual(DeviceType.UNKNOWN.value, 0)
        self.assertEqual(DeviceType.SHUTTER.value, 1)
        self.assertEqual(DeviceType.BLIND.value, 2)
        self.assertEqual(DeviceType.AWNING.value, 3)
        self.assertEqual(DeviceType.SWITCH.value, 4)
        self.assertEqual(DeviceType.DIMMER.value, 5)
        self.assertEqual(DeviceType.NIGHT_LIGHT.value, 6)
        self.assertEqual(DeviceType.DRAWN_LIGHT.value, 7)
        self.assertEqual(DeviceType.HEATING.value, 8)
        self.assertEqual(DeviceType.COOLING.value, 9)
        self.assertEqual(DeviceType.SWITCHDAY.value, 10)
        self.assertEqual(DeviceType.GATEWAY.value, 11)

    def test_selve_types_enum(self):
        """Test SelveTypes enum values."""
        self.assertEqual(SelveTypes.SERVICE.value, "service")
        self.assertEqual(SelveTypes.PARAM.value, "param")
        self.assertEqual(SelveTypes.DEVICE.value, "device")
        self.assertEqual(SelveTypes.SENSOR.value, "sensor")
        self.assertEqual(SelveTypes.SENSIM.value, "senSim")
        self.assertEqual(SelveTypes.SENDER.value, "sender")
        self.assertEqual(SelveTypes.GROUP.value, "group")
        self.assertEqual(SelveTypes.COMMAND.value, "command")
        self.assertEqual(SelveTypes.EVENT.value, "event")
        self.assertEqual(SelveTypes.IVEO.value, "iveo")
        self.assertEqual(SelveTypes.COMMEO.value, "commeo")
        self.assertEqual(SelveTypes.FIRMWARE.value, "firmware")
        self.assertEqual(SelveTypes.UNKNOWN.value, "unknown")

    def test_device_state_enum(self):
        """Test DeviceState enum values."""
        self.assertEqual(DeviceState.UNUSED.value, 0)
        self.assertEqual(DeviceState.USED.value, 1)
        self.assertEqual(DeviceState.TEMPORARY.value, 2)
        self.assertEqual(DeviceState.STALLED.value, 3)

    def test_movement_state_enum(self):
        """Test MovementState enum values."""
        self.assertEqual(MovementState.UNKOWN.value, 0)  # Note: typo in original
        self.assertEqual(MovementState.STOPPED_OFF.value, 1)
        self.assertEqual(MovementState.UP_ON.value, 2)
        self.assertEqual(MovementState.DOWN_ON.value, 3)

    def test_communication_type_enum(self):
        """Test CommunicationType enum values."""
        self.assertEqual(CommunicationType.COMMEO.value, 0)
        self.assertEqual(CommunicationType.IVEO.value, 1)
        self.assertEqual(CommunicationType.UNKNOWN.value, 99)

    def test_sensim_command_type_enum(self):
        """Test SenSimCommandType enum values."""
        self.assertEqual(SenSimCommandType.STOP.value, 0)
        self.assertEqual(SenSimCommandType.DRIVEUP.value, 1)
        self.assertEqual(SenSimCommandType.DRIVEDOWN.value, 2)
        self.assertEqual(SenSimCommandType.POSITION_1.value, 3)
        self.assertEqual(SenSimCommandType.POSITION_2.value, 4)

    def test_drive_command_commeo_enum(self):
        """Test DriveCommandCommeo enum values."""
        self.assertEqual(DriveCommandCommeo.STOP.value, 0)
        self.assertEqual(DriveCommandCommeo.DRIVEUP.value, 1)
        self.assertEqual(DriveCommandCommeo.DRIVEDOWN.value, 2)
        self.assertEqual(DriveCommandCommeo.DRIVEPOS1.value, 3)
        self.assertEqual(DriveCommandCommeo.SAVEPOS1.value, 4)
        self.assertEqual(DriveCommandCommeo.DRIVEPOS2.value, 5)
        self.assertEqual(DriveCommandCommeo.SAVEPOS2.value, 6)
        self.assertEqual(DriveCommandCommeo.DRIVEPOS.value, 7)
        self.assertEqual(DriveCommandCommeo.STEPUP.value, 8)
        self.assertEqual(DriveCommandCommeo.STEPDOWN.value, 9)
        self.assertEqual(DriveCommandCommeo.AUTOON.value, 10)
        self.assertEqual(DriveCommandCommeo.AUTOOFF.value, 11)

    def test_device_command_type_enum(self):
        """Test DeviceCommandType enum values."""
        self.assertEqual(DeviceCommandType.FORCED.value, 0)
        self.assertEqual(DeviceCommandType.MANUAL.value, 1)
        self.assertEqual(DeviceCommandType.TIME.value, 2)
        self.assertEqual(DeviceCommandType.GLASS.value, 3)

    def test_drive_command_iveo_enum(self):
        """Test DriveCommandIveo enum values."""
        self.assertEqual(DriveCommandIveo.STOP.value, 0)
        self.assertEqual(DriveCommandIveo.UP.value, 1)
        self.assertEqual(DriveCommandIveo.DOWN.value, 2)
        self.assertEqual(DriveCommandIveo.POS1.value, 3)
        self.assertEqual(DriveCommandIveo.POS2.value, 5)
        self.assertEqual(DriveCommandIveo.LEARNTELEGRAMSENT.value, 254)
        self.assertEqual(DriveCommandIveo.TEACHTELEGRAMSENT.value, 255)

    def test_parameter_type_enum(self):
        """Test ParameterType enum values."""
        self.assertEqual(ParameterType.INT.value, "int")
        self.assertEqual(ParameterType.STRING.value, "string")
        self.assertEqual(ParameterType.BASE64.value, "base64")
        self.assertEqual(ParameterType.BOOL.value, "bool")

    def test_scan_state_enum(self):
        """Test ScanState enum values."""
        self.assertEqual(ScanState.IDLE.value, 0)
        self.assertEqual(ScanState.RUN.value, 1)
        self.assertEqual(ScanState.VERIFY.value, 2)
        self.assertEqual(ScanState.END_SUCCESS.value, 3)
        self.assertEqual(ScanState.END_FAILED.value, 4)

    def test_teach_state_enum(self):
        """Test TeachState enum values."""
        self.assertEqual(TeachState.IDLE.value, 0)
        self.assertEqual(TeachState.RUN.value, 1)
        self.assertEqual(TeachState.END_SUCCESS.value, 2)

    def test_command_result_state_enum(self):
        """Test CommandResultState enum values."""
        self.assertEqual(CommandResultState.IDLE.value, 0)
        self.assertEqual(CommandResultState.SEND.value, 1)

    def test_service_state_enum(self):
        """Test ServiceState enum values."""
        self.assertEqual(ServiceState.BOOTLOADER.value, 0)
        self.assertEqual(ServiceState.UPDATE.value, 1)
        self.assertEqual(ServiceState.STARTUP.value, 2)
        self.assertEqual(ServiceState.READY.value, 3)
        self.assertEqual(ServiceState.NOT_READY.value, 4)

    def test_sensor_state_enum(self):
        """Test SensorState enum values."""
        self.assertEqual(SensorState.INVALID.value, 0)
        self.assertEqual(SensorState.AVAILABLE.value, 1)
        self.assertEqual(SensorState.LOW_BATTERY.value, 2)
        self.assertEqual(SensorState.COMMUNICATION_LOSS.value, 3)
        self.assertEqual(SensorState.TESTMODE.value, 4)
        self.assertEqual(SensorState.SERVICEMODE.value, 5)

    def test_repeater_state_enum(self):
        """Test RepeaterState enum values."""
        self.assertEqual(RepeaterState.NONE.value, 0)
        self.assertEqual(RepeaterState.SINGLEREPEAT.value, 1)
        self.assertEqual(RepeaterState.MULTIREPEAT.value, 2)

    def test_led_mode_enum(self):
        """Test LEDMode enum values."""
        self.assertEqual(LEDMode.OFF.value, 0)
        self.assertEqual(LEDMode.ON.value, 1)

    def test_forwarding_enum(self):
        """Test Forwarding enum values."""
        self.assertEqual(Forwarding.OFF.value, 0)
        self.assertEqual(Forwarding.ON.value, 1)

    def test_duty_mode_enum(self):
        """Test DutyMode enum values."""
        self.assertEqual(DutyMode.NOT_BLOCKED.value, 0)
        self.assertEqual(DutyMode.BLOCKED.value, 1)

    def test_day_mode_enum(self):
        """Test DayMode enum values."""
        self.assertEqual(DayMode.UNKOWN.value, 0)  # Note: typo in original
        self.assertEqual(DayMode.NIGHTMODE.value, 1)
        self.assertEqual(DayMode.DAWNING.value, 2)
        self.assertEqual(DayMode.DAY.value, 3)
        self.assertEqual(DayMode.DUSK.value, 4)

    def test_device_functions_enum(self):
        """Test DeviceFunctions enum values."""
        self.assertEqual(DeviceFunctions.SELECT.value, 0)
        self.assertEqual(DeviceFunctions.INSTALL.value, 1)
        self.assertEqual(DeviceFunctions.SENSOR.value, 2)
        self.assertEqual(DeviceFunctions.MANPROG.value, 3)
        self.assertEqual(DeviceFunctions.AUTOPROG.value, 4)
        self.assertEqual(DeviceFunctions.STOREPOSITION.value, 5)
        self.assertEqual(DeviceFunctions.DRIVEUP.value, 6)
        self.assertEqual(DeviceFunctions.DRIVEDOWN.value, 7)
        self.assertEqual(DeviceFunctions.KEYRELEASE.value, 8)
        self.assertEqual(DeviceFunctions.DRIVESTOP.value, 9)

    def test_log_type_enum(self):
        """Test LogType enum values."""
        self.assertEqual(LogType.INFO.value, 0)
        self.assertEqual(LogType.WARNING.value, 1)
        self.assertEqual(LogType.ERROR.value, 2)

    def test_device_class_enum(self):
        """Test DeviceClass enum values."""
        self.assertEqual(DeviceClass.ACTOR.value, 0)
        self.assertEqual(DeviceClass.GROUP.value, 1)
        self.assertEqual(DeviceClass.SENDER.value, 2)
        self.assertEqual(DeviceClass.SENSIM.value, 3)
        self.assertEqual(DeviceClass.SENSOR.value, 4)
        self.assertEqual(DeviceClass.IVEO.value, 5)
        self.assertEqual(DeviceClass.UNKOWN.value, 99)  # Note: typo in original

    def test_sensor_variable_enums(self):
        """Test sensor variable enums."""
        # windDigital
        self.assertEqual(windDigital.NONE.value, 0)
        self.assertEqual(windDigital.NO_ALARM.value, 1)
        self.assertEqual(windDigital.ALARM.value, 2)
        
        # rainDigital
        self.assertEqual(rainDigital.NONE.value, 0)
        self.assertEqual(rainDigital.NO_ALARM.value, 1)
        self.assertEqual(rainDigital.ALARM.value, 2)
        
        # tempDigital
        self.assertEqual(tempDigital.NONE.value, 0)
        self.assertEqual(tempDigital.NORMAL.value, 1)
        self.assertEqual(tempDigital.FREEZING.value, 2)
        self.assertEqual(tempDigital.HEAT.value, 3)
        
        # lightDigital
        self.assertEqual(lightDigital.NONE.value, 0)
        self.assertEqual(lightDigital.DARK.value, 1)
        self.assertEqual(lightDigital.DAWN.value, 2)
        self.assertEqual(lightDigital.NORMAL.value, 3)
        self.assertEqual(lightDigital.LIGHT.value, 4)

    def test_sender_events_enum(self):
        """Test senderEvents enum values."""
        self.assertEqual(senderEvents.UNKNOWN.value, 0)
        self.assertEqual(senderEvents.DRIVEUP.value, 1)
        self.assertEqual(senderEvents.DRIVEDOWN.value, 2)
        self.assertEqual(senderEvents.STOP.value, 3)
        self.assertEqual(senderEvents.POS1.value, 4)
        self.assertEqual(senderEvents.POS2.value, 5)
        self.assertEqual(senderEvents.SAVEPOS1.value, 6)
        self.assertEqual(senderEvents.SAVEPOS2.value, 7)
        self.assertEqual(senderEvents.AUTO.value, 8)
        self.assertEqual(senderEvents.MAN.value, 9)
        self.assertEqual(senderEvents.NAME.value, 10)
        self.assertEqual(senderEvents.KEYRELEASE.value, 11)
        self.assertEqual(senderEvents.SELECT.value, 12)
        self.assertEqual(senderEvents.DELETE.value, 13)

    def test_enum_membership(self):
        """Test enum membership and iteration."""
        # Test that we can iterate over enum values
        device_types = list(DeviceType)
        self.assertGreater(len(device_types), 0)
        self.assertIn(DeviceType.SHUTTER, device_types)
        
        # Test enum membership
        self.assertIn(DeviceType.BLIND, DeviceType)
        self.assertEqual(DeviceType.BLIND.name, 'BLIND')

    def test_enum_comparisons(self):
        """Test enum comparisons and identity."""
        # Test equality
        self.assertEqual(DeviceType.SHUTTER, DeviceType.SHUTTER)
        self.assertNotEqual(DeviceType.SHUTTER, DeviceType.BLIND)
        
        # Test identity
        self.assertIs(DeviceType.SHUTTER, DeviceType(1))
        
        # Test value access
        self.assertEqual(DeviceType.SHUTTER.value, 1)


if __name__ == '__main__':
    unittest.main()
