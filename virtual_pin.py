# Z-Probe support
#
#
# This file may be distributed under the terms of the GNU GPLv3 license.

import logging
import pins
import buttons

# virtual pin implementations from https://github.com/Klipper3d/klipper/pull/5883
# Copyright (C) 2022  Pedro Lamas <pedrolamas@gmail.com>

class VirtualPin:
    def __init__(self, parent, pin_params):
        self._vchip = vchip
        self._name = pin_params['pin']
        self._pullup = pin_params['pullup']
        self._invert = pin_params['invert']
        self._mcu = printer.lookup_object('mcu')
    #     gcode = printer.lookup_object('gcode')
    #     gcode.register_mux_command("SET_VIRTUAL_PIN", "PIN", self._name,
    #                                self.cmd_SET_VIRTUAL_PIN,
    #                                desc=self.cmd_SET_VIRTUAL_PIN_help)

    # cmd_SET_VIRTUAL_PIN_help = "Set the value of an output pin"
    # def cmd_SET_VIRTUAL_PIN(self, gcmd):
    #     self._value = gcmd.get_float('VALUE', minval=0., maxval=1.)

    def get_mcu(self):
        return self._mcu
    def _get_hw_value(self):
        return self._vchip._get_hw_value(self._pullup, self._invert)

# Notes - No interest in binding this to physical pin
# do NOT want to deal with multiple writer scenario
# @TODO one-writer-multiple-reader scenario is a possibility.
# advantage over actual variable is that it can be configured as a pin
class DigitalOutVirtualPin(VirtualPin):
    def __init__(self, mcu, pin_params):
        VirtualPin.__init__(self, mcu, pin_params)

    def setup_max_duration(self, max_duration):
        pass

    def setup_start_value(self, start_value, shutdown_value):
        self._value = start_value

    def set_digital(self, print_time, value):
        self._value = value

    def get_status(self, eventtime):
        return {
            'value': self._value,
            'type': 'digital_out'
        }

class PwmVirtualPin(VirtualPin):
    def __init__(self, mcu, pin_params):
        VirtualPin.__init__(self, mcu, pin_params)

    def setup_max_duration(self, max_duration):
        pass

    def setup_start_value(self, start_value, shutdown_value):
        self._value = start_value

    def setup_cycle_time(self, cycle_time, hardware_pwm=False):
        pass

    def set_pwm(self, print_time, value, cycle_time=None):
        self._value = value

    def get_status(self, eventtime):
        return {
            'value': self._value,
            'type': 'pwm'
        }

class AdcVirtualPin(VirtualPin):
    def __init__(self, mcu, pin_params):
        VirtualPin.__init__(self, mcu, pin_params)
        self._callback = None
        self._min_sample = 0.
        self._max_sample = 0.
        printer = self._mcu.get_printer()
        printer.register_event_handler("klippy:connect",
                                            self.handle_connect)

    def handle_connect(self):
        reactor = self._mcu.get_printer().get_reactor()
        reactor.register_timer(self._raise_callback, reactor.monotonic() + 2.)

    def setup_adc_callback(self, report_time, callback):
        self._callback = callback

    def setup_minmax(self, sample_time, sample_count,
                     minval=0., maxval=1., range_check_count=0):

        self._min_sample = minval
        self._max_sample = maxval

    def _raise_callback(self, eventtime):
        range = self._max_sample - self._min_sample
        sample_value = (_get_hw_value() * range) + self._min_sample
        self._callback(eventtime, sample_value)

    def get_status(self, eventtime):
        return {
            'value': _get_hw_value(),
            'type': 'adc'
        }

class EndstopVirtualPin(VirtualPin):
    def __init__(self, mcu, pin_params):
        VirtualPin.__init__(self, mcu, pin_params)
        self._steppers = []

    def add_stepper(self, stepper):
        self._steppers.append(stepper)

    def query_endstop(self, print_time):
        return _get_hw_value()

    def home_start(self, print_time, sample_time, sample_count, rest_time,
                   triggered=True):
        reactor = self._mcu.get_printer().get_reactor()
        completion = reactor.completion()
        completion.complete(True)
        return completion

    def home_wait(self, home_end_time):
        return 1

    def get_steppers(self):
        return list(self._steppers)

    def get_status(self, eventtime):
        return {
            'value': _get_hw_value(),
            'type': 'endstop'
        }

# Non-copied code

class VirtualMCU:
    def __init__(self, config, mcu_probe):
        self.printer = config.get_printer()
        self.name = config.get_name()
        self._adc_handlers = []
        self._endstop_handlers = []
        self._pin_names = set() # We still want to enforce no-dupes, as long as klipper does by default
        # Set up listener on actual pin
        ppins = self.printer.lookup_object('pins')
        pin = config.get('source_pin') # theoretically, this could be 
        pin_params = ppins.lookup_pin(pin, can_invert=True, can_pullup=True)
        mcu = pin_params['chip']
        self.hw_pin = mcu.setup_pin('adc', pin_params)
        self.hw_pin.setup_minmax(ADC_SAMPLE_TIME, ADC_SAMPLE_COUNT)
        self.mcu_adc.setup_adc_callback(ADC_REPORT_TIME, self.hw_callback)

        self.printer.lookup_object('pins').register_chip(self.qualified_name(), self)

        # self.gcode = self.printer.lookup_object('gcode')
        # self.gcode.register_command('PROBE', self.cmd_PROBE,
                                    # desc=self.cmd_PROBE_help)

    def qualified_name(self):
        return f'vpin_{self.name}' #don't want to deal with naming collisions, add vpin

    def setup_pin(self, pin_type, pin_params):
        ppins = self._printer.lookup_object('pins')
        if self._pin_names.contains(pin_params['pin']):
            raise pins.error(f'Duplicate registration for {self.qualified_name()}:{pin_params["pin"]}')
        if pin_type == 'digital_out':
            raise pins.error(f'{self.qualified_name()}: {pin_params["pin"]} digital_out not implemented')
            # pin = DigitalOutVirtualPin(self, pin_params)
        elif pin_type == 'pwm':
            raise pins.error(f'{self.qualified_name()}: {pin_params["pin"]} pwm not implemented')
            # pin = PwmVirtualPin(self, pin_params)
        elif pin_type == 'adc':
            pin = AdcVirtualPin(self, pin_params)
            self._adc_handlers.append(pin)
        elif pin_type == 'endstop':
            pin = EndstopVirtualPin(self, pin_params)
            self._endstop_handler.append(pin)
        else:
            raise ppins.error(f'unable to create virtual pin of type {pin_type}')

        return pin

    def _get_hw_value(self, invert, pullup):
        curtime = self._printer.get_reactor().monotonic()
        val = self.hw_pin.get_status(curtime)['value']

def load_config(config):
    return VirtualMCU(config)