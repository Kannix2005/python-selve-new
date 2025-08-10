import unittest
from selve.commands.command import (
    CommeoCommand, CommandStop, CommandDriveUp, CommandDriveDown,
    CommandDrivePos1, CommandSavePos1, CommandDrivePos2, CommandSavePos2,
    CommandDrivePos, CommandStopGroup, CommandDriveUpGroup, CommandDriveDownGroup
)
from selve.util import DriveCommandCommeo, DeviceCommandType


class TestCommeoCommands(unittest.TestCase):

    def test_commeo_command_initialization(self):
        """Test initialization of a CommeoCommand."""
        cmd = CommeoCommand(1, DriveCommandCommeo.STOP, DeviceCommandType.MANUAL)
        self.assertEqual(cmd.method_name, "selve.GW.command.device")
        self.assertEqual(len(cmd.parameters), 4)  # Should have 4 parameters

    def test_command_stop(self):
        """Test creation of a stop command."""
        cmd = CommandStop(1, DeviceCommandType.MANUAL)
        self.assertEqual(cmd.method_name, "selve.GW.command.device")
        self.assertEqual(cmd.parameters[0][1], 1)  # device ID
        self.assertEqual(cmd.parameters[1][1], DriveCommandCommeo.STOP.value)  # stop command
        self.assertEqual(cmd.parameters[2][1], DeviceCommandType.MANUAL.value)  # manual mode
        self.assertEqual(cmd.parameters[3][1], 0)  # param

    def test_command_drive_up(self):
        """Test creation of a drive up command."""
        cmd = CommandDriveUp(1, DeviceCommandType.MANUAL)
        self.assertEqual(cmd.method_name, "selve.GW.command.device")
        self.assertEqual(cmd.parameters[0][1], 1)  # device ID
        self.assertEqual(cmd.parameters[1][1], DriveCommandCommeo.DRIVEUP.value)  # drive up command
        self.assertEqual(cmd.parameters[2][1], DeviceCommandType.MANUAL.value)  # manual mode
        self.assertEqual(cmd.parameters[3][1], 0)  # param

    def test_command_drive_down(self):
        """Test creation of a drive down command."""
        cmd = CommandDriveDown(1, DeviceCommandType.MANUAL)
        self.assertEqual(cmd.method_name, "selve.GW.command.device")
        self.assertEqual(cmd.parameters[0][1], 1)  # device ID
        self.assertEqual(cmd.parameters[1][1], DriveCommandCommeo.DRIVEDOWN.value)  # drive down command
        self.assertEqual(cmd.parameters[2][1], DeviceCommandType.MANUAL.value)  # manual mode
        self.assertEqual(cmd.parameters[3][1], 0)  # param

    def test_command_drive_pos1(self):
        """Test creation of a drive to position 1 command."""
        cmd = CommandDrivePos1(1, DeviceCommandType.MANUAL)
        self.assertEqual(cmd.method_name, "selve.GW.command.device")
        self.assertEqual(cmd.parameters[0][1], 1)  # device ID
        self.assertEqual(cmd.parameters[1][1], DriveCommandCommeo.DRIVEPOS1.value)  # drive pos1 command
        self.assertEqual(cmd.parameters[2][1], DeviceCommandType.MANUAL.value)  # manual mode
        self.assertEqual(cmd.parameters[3][1], 0)  # param

    def test_command_with_param(self):
        """Test creation of a command with a non-default parameter."""
        cmd = CommandDrivePos(1, DeviceCommandType.MANUAL, 50)  # Drive to 50% position
        self.assertEqual(cmd.method_name, "selve.GW.command.device")
        self.assertEqual(cmd.parameters[0][1], 1)  # device ID
        self.assertEqual(cmd.parameters[1][1], DriveCommandCommeo.DRIVEPOS.value)  # drive pos command
        self.assertEqual(cmd.parameters[2][1], DeviceCommandType.MANUAL.value)  # manual mode
        self.assertEqual(cmd.parameters[3][1], 50)  # param = 50%

    def test_group_commands(self):
        """Test creation of group commands."""
        # Test stop group command
        stop_group = CommandStopGroup(1, DeviceCommandType.MANUAL)
        self.assertEqual(stop_group.method_name, "selve.GW.command.group")
        self.assertEqual(stop_group.parameters[0][1], 1)  # group ID
        self.assertEqual(stop_group.parameters[1][1], DriveCommandCommeo.STOP.value)  # stop command
        self.assertEqual(stop_group.parameters[2][1], DeviceCommandType.MANUAL.value)  # manual mode
        self.assertEqual(stop_group.parameters[3][1], 0)  # param
        
        # Test drive up group command
        up_group = CommandDriveUpGroup(1, DeviceCommandType.MANUAL)
        self.assertEqual(up_group.method_name, "selve.GW.command.group")
        self.assertEqual(up_group.parameters[0][1], 1)  # group ID
        self.assertEqual(up_group.parameters[1][1], DriveCommandCommeo.DRIVEUP.value)  # drive up command
        
        # Test drive down group command
        down_group = CommandDriveDownGroup(1, DeviceCommandType.MANUAL)
        self.assertEqual(down_group.method_name, "selve.GW.command.group")
        self.assertEqual(down_group.parameters[0][1], 1)  # group ID
        self.assertEqual(down_group.parameters[1][1], DriveCommandCommeo.DRIVEDOWN.value)  # drive down command


if __name__ == "__main__":
    unittest.main()
