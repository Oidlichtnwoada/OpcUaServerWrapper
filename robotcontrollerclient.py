from time import sleep

from opcua import ua

from telnetclient import TelnetClient


class RobotControllerClient:
    TEST_COMMAND = '1;1;TIME'
    ENCODING = 'ascii'
    START_SEQUENCE_SUCCESS = 'QoK'
    START_SEQUENCE_ERROR = 'QeR'
    DELIMITER = ';'
    TIMEOUT = 0.1

    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.client = TelnetClient(self.ip, self.port, timeout=self.TIMEOUT, setup_method=self.setup_controller,
                                   test_command=self.TEST_COMMAND, encoding=self.ENCODING)
        self.setup_controller()
        self.program_list = []
        self.initialize_program_list()

    def initialize_program_list(self, robot_number=1, slot_number=1):
        while True:
            try:
                self.program_list.clear()
                self.initialize_all_slots(robot_number, slot_number)
                while self.get_current_program(robot_number, slot_number) not in self.program_list:
                    self.program_list.append(self.get_current_program(robot_number, slot_number))
                    self.scroll_up_to_next_program(robot_number, slot_number)
                break
            except RobotControllerError:
                sleep(1)

    def initialize_all_slots(self, robot_number=1, slot_number=1):
        if not self.is_running(robot_number, slot_number):
            self.process_request(f'{robot_number};{slot_number};SLOTINIT')
        else:
            raise RobotControllerError(ua.StatusCodes.BadInvalidState)

    def process_request(self, req, timeout_factor=1):
        res = self.client.send_request_and_return_response(req, timeout_factor)
        if res.startswith(self.START_SEQUENCE_SUCCESS):
            return res[len(self.START_SEQUENCE_SUCCESS):].split(self.DELIMITER)
        else:
            raise RobotControllerError(ua.StatusCodes.BadCommunicationError, res[len(self.START_SEQUENCE_ERROR):])

    def scroll_up_to_next_program(self, robot_number=1, slot_number=1):
        self.process_request(f'{robot_number};{slot_number};PRGUP')

    def get_current_program(self, robot_number=1, slot_number=1):
        return self.process_request(f'{robot_number};{slot_number};PRGRD')[0][:-4]

    def get_override(self, robot_number=1, slot_number=1):
        return int(self.process_request(f'{robot_number};{slot_number};OVRD')[0])

    def set_override(self, percentage, robot_number=1, slot_number=1):
        self.process_request(f'{robot_number};{slot_number};OVRD={percentage}')

    def get_parameter(self, name, robot_number=1, slot_number=1):
        return self.process_request(f'{robot_number};{slot_number};PAR{name}')[1]

    def set_parameter(self, name, value, robot_number=1, slot_number=1):
        self.process_request(f'{robot_number};{slot_number};PAW={name};{value}')

    def stop_immediately(self, robot_number=1, slot_number=1):
        self.process_request(f'{robot_number};{slot_number};STOP')
        self.turn_servos_off(robot_number, slot_number)

    def stop_at_next_cycle(self, robot_number=1, slot_number=1):
        self.process_request(f'{robot_number};{slot_number};CSTOP')

    def is_running(self, robot_number=1, slot_number=1):
        run_status = int(self.process_request(f'{robot_number};{slot_number};STATE')[4][:2], 16)
        return bool(int(f'{run_status:08b}'[1]))

    def move_to_safe_position(self, robot_number=1, slot_number=1):
        if not self.is_running(robot_number, slot_number):
            self.turn_servos_on(robot_number, slot_number)
            self.process_request(f'{robot_number};{slot_number};MOVSP')
        else:
            raise RobotControllerError(ua.StatusCodes.BadInvalidState)

    def resume_program(self, program_name, repeated, robot_number=1, slot_number=1):
        if program_name not in self.program_list:
            raise RobotControllerError(ua.StatusCodes.BadInvalidArgument)
        if self.is_running(robot_number, slot_number):
            raise RobotControllerError(ua.StatusCodes.BadInvalidState)
        if self.get_current_program(robot_number, slot_number) != program_name:
            self.initialize_all_slots(robot_number, slot_number)
            self.process_request(f'{robot_number};{slot_number};PRGLOAD={program_name}')
        self.turn_servos_on(robot_number, slot_number)
        self.process_request(f'{robot_number};{slot_number};RUN{program_name};{int(not repeated)}')

    def reset_error(self, robot_number=1, slot_number=1):
        self.process_request(f'{robot_number};{slot_number};RSTALRM')

    def reset_program(self, robot_number=1, slot_number=1):
        if not self.is_running(robot_number, slot_number):
            self.process_request(f'{robot_number};{slot_number};RSTPRG')
        else:
            raise RobotControllerError(ua.StatusCodes.BadInvalidState)

    def turn_servos_on(self, robot_number=1, slot_number=1):
        self.process_request(f'{robot_number};{slot_number};SRVON')
        sleep(2)

    def turn_servos_off(self, robot_number=1, slot_number=1):
        self.process_request(f'{robot_number};{slot_number};SRVOFF', timeout_factor=20)

    def get_most_recent_error(self, robot_number=1, slot_number=1):
        return self.process_request(f'{robot_number};{slot_number};ERRORLOGTOP')[3]

    def setup_controller(self, robot_number=1, slot_number=1):
        while True:
            try:
                self.process_request(f'{robot_number};{slot_number};CNTLON')
                break
            except RobotControllerError:
                sleep(1)

    def read_input(self, index, robot_number=1, slot_number=1):
        return int(self.process_request(f'{robot_number};{slot_number};IN{index}')[0], 16)

    def write_output(self, index, value, robot_number=1, slot_number=1):
        self.process_request(f'{robot_number};{slot_number};OUT={index};{value:04x}')

    def open_gripper(self, hand_number=1, robot_number=1, slot_number=1):
        self.process_request(f'{robot_number};{slot_number};HNDON{hand_number}')

    def close_gripper(self, hand_number=1, robot_number=1, slot_number=1):
        self.process_request(f'{robot_number};{slot_number};HNDOFF{hand_number}')

    def move(self, x, y, z, a, b, c, robot_number=1, slot_number=1):
        self.process_request(
            f'{robot_number};{slot_number};EXEC2=TEMP=({x:.0f},{y:.0f},{z:.0f},{a:.0f},{b:.0f},{c:.0f})')
        self.process_request(f'{robot_number};{slot_number};EXEC2=MOV TEMP')


class RobotControllerError(Exception):
    def __init__(self, status_code, error_code=None):
        Exception.__init__(self)
        self.status_code = status_code
        self.error_code = error_code
