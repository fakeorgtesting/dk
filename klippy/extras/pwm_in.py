# Support for GPIO input edge counters
#
# Copyright (C) 2021  Adrian Keet <arkeet@gmail.com>
#
# This file may be distributed under the terms of the GNU GPLv3 license.
# import logging

class MCU_pwm_in:
    def __init__(self, printer, pin, interval, timeout, additional_timeout_ticks, pwm_frequency):
        ppins = printer.lookup_object("pins")
        pin_params = ppins.lookup_pin(pin, can_pullup=True)
        self._mcu = pin_params["chip"]
        self._oid = self._mcu.create_oid()
        self._pin = pin_params["pin"]
        self._pullup = pin_params["pullup"]
        self._interval = interval
        self._pwm_frequency = pwm_frequency
        self._timeout = timeout
        self._additional_timeout_ticks = additional_timeout_ticks
        self._callback = None
        self.duty_cycle = 0.0
        self._mcu.register_config_callback(self.build_config)

    def build_config(self):
        self._mcu.add_config_cmd(
            "config_pwm_in oid=%d pin=%s pull_up=%d"
            % (self._oid, self._pin, self._pullup)
        )
        clock = self._mcu.get_query_slot(self._oid)
        interval_ticks = self._mcu.seconds_to_clock(self._interval)
        timeout_ticks = self._mcu.seconds_to_clock(self._timeout) + self._additional_timeout_ticks
        self._mcu.add_config_cmd(
            "query_pwm_in oid=%d clock=%d interval=%d max_task_ticks=%d"
            % (self._oid, clock, interval_ticks, timeout_ticks),
            is_init=True,
        )
        self._mcu.register_response(
            self._handle_pwm_in_state, "pwm_in_state", self._oid
        )

    # Callback is called periodically every sample_time
    def setup_callback(self, cb):
        self._callback = cb

    def _handle_pwm_in_state(self, params):
        high_ticks = params["high_ticks"]
        pulse_width = self._mcu.ticks_to_seconds(high_ticks)
        # given pulse_width, use frequency to calculate duty cycle
        duty_cycle = pulse_width * self._pwm_frequency
        # logging.info(f"duty cycle: {duty_cycle}")
        self._duty_cycle = duty_cycle
        if self._callback is not None:
            self._callback(duty_cycle)


class PWMIn:
    def __init__(self, printer, pin, read_interval, pwm_frequency, additional_timeout_ticks):
        self._callback = None
        self._last_time = self._last_count = None
        self._pwm_frequency = (
            pwm_frequency  # pulses / second at 100% duty cycle
        )
        self._read_interval = read_interval
        # timeout is the maximum time to wait for a pulse before assuming 0% duty cycle
        self._timeout = 1.0 / pwm_frequency
        self._additional_timeout_ticks = additional_timeout_ticks
        self._duty_cycle = 0.0
        self._mcu_pwm_in = MCU_pwm_in(
            printer,
            pin,
            self._read_interval,
            self._timeout,
            self._additional_timeout_ticks,
            self._pwm_frequency,
        )
        self._mcu_pwm_in.setup_callback(self._pwm_in_callback)

    def _pwm_in_callback(self, duty_cycle):
        self._duty_cycle = duty_cycle
        if self._callback is not None:
            self._callback(self._duty_cycle)

    def setup_callback(self, cb):
        self._callback = cb

    def get_duty_cycle(self):
        return self._duty_cycle
