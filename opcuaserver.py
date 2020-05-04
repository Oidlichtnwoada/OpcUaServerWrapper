from threading import Thread
from time import sleep

from opcua import Server, ua, uamethod

from robotcontrollerclient import RobotControllerClient as RCClient, RobotControllerError


class OpcUaServerForRobotController:

    def __init__(self, ip_os, port_os, ip_rc, port_rc):
        self.rc_client = RCClient(ip_rc, port_rc)
        self.opc_ua_server = Server()
        self.opc_ua_server.set_endpoint(f'opc.tcp://{ip_os}:{port_os}/')
        self.opc_ua_server.set_security_policy([ua.SecurityPolicyType.NoSecurity])
        self.opc_ua_server.set_server_name(self.__class__.__name__)
        self.opc_ua_server.import_xml('./Opc.Ua.NodeSet2.xml')
        self.opc_ua_server.import_xml('./Opc.Ua.Di.NodeSet2.xml')
        self.opc_ua_server.import_xml('./Opc.Ua.Robotics.NodeSet2.xml')
        self.opc_ua_server.import_xml('./Tuw.Auto.MitsubishiElectricRobot.NodeSet2.xml')
        self.link_method('ns=4;i=1115', self.move_to_safe_position)
        self.link_method('ns=4;i=1069', self.set_override)
        self.link_method('ns=4;i=1075', self.set_parameter)
        self.link_method('ns=4;i=1072', self.get_parameter)
        self.link_method('ns=4;i=1105', self.get_most_recent_error)
        self.link_method('ns=4;i=1119', self.stop_immediately)
        self.link_method('ns=4;i=1108', self.reset_error)
        self.generate_task_controls()

    def link_method(self, node_id, method):
        self.opc_ua_server.link_method(self.opc_ua_server.get_node(node_id), method)

    def generate_task_controls(self):
        self.opc_ua_server.get_node('ns=4;i=1038').delete(recursive=True)
        task_controls_object = self.opc_ua_server.get_node('ns=4;i=1022')
        for index, program_name in enumerate(self.rc_client.program_list):
            task_control_object = task_controls_object \
                .add_object(f'ns=1;i={index + 1}', f'TaskControlFor{program_name}', 'ns=3;i=1011')
            task_controls_object.delete_reference(task_control_object.nodeid, reftype=ua.ObjectIds.Organizes)
            task_controls_object.add_reference(task_control_object.nodeid, reftype=ua.ObjectIds.HasComponent)
            task_control_object.get_child(['3:<MotionDeviceIdentifier>']).delete(recursive=True)
            task_control_object.get_child(['2:ParameterSet', '3:TaskProgramName']).set_data_value(program_name)
            self.link_method(task_control_object.get_child(['2:MethodSet', '4:ResetProgram']).
                             nodeid, self.reset_program)
            self.link_method(task_control_object.get_child(['2:MethodSet', '4:StopAtNextCycle']).
                             nodeid, self.stop_at_next_cycle)
            self.link_method(task_control_object.get_child(['2:MethodSet', '4:ResumeProgram']).
                             nodeid, self.resume_program)

    def periodic_routine(self):
        self.opc_ua_server.get_node('ns=4;i=1033').set_data_value(self.rc_client.get_override())
        self.opc_ua_server.get_node('ns=4;i=1122').set_data_value(self.rc_client.is_running())
        for index, program_name in enumerate(self.rc_client.program_list):
            self.opc_ua_server.get_node('ns=4;i=1022') \
                .get_child([f'0:TaskControlFor{program_name}', '2:ParameterSet', '3:TaskProgramLoaded']) \
                .set_data_value(program_name == self.rc_client.get_current_program())

    def get_program_name_from_parent_node(self, parent):
        return self.opc_ua_server.get_node(parent).get_parent() \
            .get_child(['2:ParameterSet', '3:TaskProgramName']).get_data_value().Value.Value

    def start(self):
        self.opc_ua_server.start()
        PeriodicWorker(self).start()

    @staticmethod
    def error_response(status_code):
        return ua.StatusCode(status_code)

    @uamethod
    def set_override(self, parent, percentage):
        try:
            self.rc_client.set_override(percentage)
        except RobotControllerError as rce:
            return self.error_response(rce.status_code)

    @uamethod
    def get_parameter(self, parent, name):
        try:
            return self.rc_client.get_parameter(name)
        except RobotControllerError as rce:
            return self.error_response(rce.status_code)

    @uamethod
    def set_parameter(self, parent, name, value):
        try:
            return self.rc_client.set_parameter(name, value)
        except RobotControllerError as rce:
            return self.error_response(rce.status_code)

    @uamethod
    def stop_immediately(self, parent):
        try:
            self.rc_client.stop_immediately()
        except RobotControllerError as rce:
            return self.error_response(rce.status_code)

    @uamethod
    def stop_at_next_cycle(self, parent):
        if self.get_program_name_from_parent_node(parent) == self.rc_client.get_current_program():
            try:
                return self.rc_client.stop_at_next_cycle()
            except RobotControllerError as rce:
                return self.error_response(rce.status_code)
        else:
            return self.error_response(ua.StatusCodes.BadInvalidState)

    @uamethod
    def move_to_safe_position(self, parent):
        try:
            return self.rc_client.move_to_safe_position()
        except RobotControllerError as rce:
            return self.error_response(rce.status_code)

    @uamethod
    def resume_program(self, parent, repeated):
        try:
            program_name = self.get_program_name_from_parent_node(parent)
            return self.rc_client.resume_program(program_name, repeated)
        except RobotControllerError as rce:
            return self.error_response(rce.status_code)

    @uamethod
    def reset_error(self, parent):
        try:
            return self.rc_client.reset_error()
        except RobotControllerError as rce:
            return self.error_response(rce.status_code)

    @uamethod
    def reset_program(self, parent):
        if self.get_program_name_from_parent_node(parent) == self.rc_client.get_current_program():
            try:
                self.rc_client.reset_program()
            except RobotControllerError as rce:
                return self.error_response(rce.status_code)
        else:
            return self.error_response(ua.StatusCodes.BadInvalidState)

    @uamethod
    def get_most_recent_error(self, parent):
        try:
            return self.rc_client.get_most_recent_error()
        except RobotControllerError as rce:
            return self.error_response(rce.status_code)


class PeriodicWorker(Thread):
    def __init__(self, server):
        Thread.__init__(self)
        self.server = server

    def run(self):
        while True:
            try:
                self.server.periodic_routine()
            except RobotControllerError:
                pass
            sleep(10)
