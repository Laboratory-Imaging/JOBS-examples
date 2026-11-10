"""One Aria SDK session per process. stdout is reserved for JSON events."""
from __future__ import annotations

import argparse
from collections import deque
import importlib
import json
import os
import queue
import socket
import sys
import threading
import time
import traceback


def enum_name(value):
    return str(value).rsplit('.', 1)[-1]


class Worker:
    START_TIMEOUT = 60.0
    STOP_TIMEOUT = 300.0
    RETRY_INTERVAL = 10.0

    def __init__(self, sdk, run_id, emit, commands):
        self.sdk = sdk
        self.run_id = run_id
        self.emit = emit
        self.commands = commands
        self.server = None
        self.conn = None
        self.state = 'ready'
        self.settings = {}
        self.steps = []
        self.pending = deque()
        self.checkpoint = 0
        self.ack = None
        self.retry = None
        self.paused = False
        self.last_step = None
        self.step_started = time.monotonic()
        self.next_status = 0.0
        self.exit_code = 0
        self.stop_reason = ''
        self.stop_event = 'cancelled'

    def log(self, message):
        print(f'[Aria worker {os.getpid()} {self.run_id}] {message}', file=sys.stderr, flush=True)

    def check(self, error, operation):
        if error != -1:
            message = self.sdk.Error.GetErrorMessage(error)
            raise RuntimeError(f'{operation}: {message} (SDK error {error})')

    def read(self, function, *args):
        value, error = function(*args)
        self.check(error, getattr(function, '__name__', str(function)))
        return value

    def send_event(self, event, **values):
        self.emit(dict(event=event, run_id=self.run_id, pid=os.getpid(), **values))

    def start(self, command):
        if self.state != 'ready':
            raise RuntimeError('A worker can start only one sequence')
        self.settings = command.get('settings') or {}
        self.state = 'initializing'
        if self.read(self.sdk.Monitoring.IsSequenceRunning):
            raise RuntimeError('Fresh SDK already has a running sequence')
        success, error = self.sdk.Instrument.LoadPhysicalInstrument()
        if not success:
            if error != -1:
                self.log(self.sdk.Error.GetErrorMessage(error))
            if not self.settings.get('enable_simulated_instrument', False):
                raise RuntimeError('No physical Aria instrument connected')
            self.check(self.sdk.Instrument.LoadSimulatedInstrument(
                self.sdk.Enums.FlowUnitType.L, self.sdk.Enums.SwitchType.MSwitch), 'load simulated instrument')
        port = self.read(self.sdk.AriaIO.GetTCPPort)
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind(('127.0.0.1', port))
        self.server.listen(1)
        self.server.setblocking(False)
        self.log(f'listening on {self.server.getsockname()}')
        self.check(self.sdk.AriaIO.SetTCPMode(False), 'set TCP client mode')
        self.check(self.sdk.Sequence.LoadSequenceFromJSON(command['sequence_json']), 'load sequence')
        # The SDK loader reads the sequence's settings. Only explicit overrides
        # are applied; this process has no configuration from a previous run.
        for key, setter in (
            ('enable_prefill', self.sdk.Sequence.EnablePrefill),
            ('enable_zero_pressure_mode', self.sdk.Sequence.EnableZeroPessureMode),
        ):
            if self.settings.get(key) is not None:
                self.check(setter(self.settings[key]), key)
        preset = self.settings.get('prefill_and_preload_flow_rate')
        if preset is not None:
            presets = {name.lower(): getattr(self.sdk.FlowRatePreset, name)
                       for name in ('Precision', 'Balanced', 'Fast', 'Max')}
            if preset.lower() not in presets:
                raise ValueError(f'Unknown prefill/preload flow-rate preset: {preset}')
            self.check(self.sdk.Configuration.SetPrefillAndPreloadFlowRate(presets[preset.lower()]), 'set flow preset')
        count = self.read(self.sdk.StepList.GetSequenceStepCount)
        self.steps = [self.step_info(i) for i in range(count)]
        self.wait_count = sum(step['type'] == 'WaitForExternalSignal' for step in self.steps)
        self.configuration = dict(
            prefill=self.read(self.sdk.Sequence.IsPrefillEnabled),
            zero_pressure=self.read(self.sdk.Sequence.IsZeroPressureModeEnabled),
            flow_rate_preset=enum_name(self.read(self.sdk.Configuration.GetPrefillAndPreloadFlowRatePreset)))
        self.log(f'effective configuration={self.configuration}; overrides={self.settings}')
        self.check(self.sdk.Sequence.StartSequence(), 'start sequence')
        self.state = 'starting'
        self.start_deadline = time.monotonic() + self.START_TIMEOUT
        self.log(f'SDK={getattr(self.sdk, "__version__", "unknown")}; sequence started')

    def step_info(self, idx):
        step_type = enum_name(self.read(self.sdk.Step.GetStepType, idx))
        parameters = {}
        specs = {
            'Flush': [('INPUT_RESERVOIR', 'int'), ('FLOWRATE', 'float')],
            'TimeInjection': [('INPUT_RESERVOIR', 'int'), ('OUTPUT_DESTINATION', 'int'), ('FLOWRATE', 'float'), ('DURATION', 'int')],
            'VolumeInjection': [('INPUT_RESERVOIR', 'int'), ('OUTPUT_DESTINATION', 'int'), ('FLOWRATE', 'float'), ('VOLUME', 'float')],
            'Wait': [('DURATION', 'int')],
            'WaitForUser': [('DURATION', 'int')],
            'WaitForExternalSignal': [('AWAITED_SIGNAL_TYPE', 'signal'), ('BACKTRACK', 'bool'), ('DURATION', 'int')],
            'SendExternalSignal': [('SIGNAL_MESSAGE', 'str')],
        }
        getters = {'int': self.sdk.Step.GetIntParameter, 'float': self.sdk.Step.GetFloatParameter,
                   'bool': self.sdk.Step.GetBoolParameter, 'str': self.sdk.Step.GetStringParameter,
                   'signal': self.sdk.Step.GetSignalTypeParameter}
        for name, kind in specs.get(step_type, []):
            value = self.read(getters[kind], idx, getattr(self.sdk.StepParameter, name))
            parameters[name] = enum_name(value) if kind == 'signal' else value
        return dict(type=step_type, parameters=parameters,
                    estimated_duration=self.read(self.sdk.Step.GetEstimatedStepDuration, idx))

    def accept_and_poll(self):
        if self.conn is None:
            try:
                self.conn, addr = self.server.accept()
                self.conn.setblocking(False)
                self.log(f'TCP peer={addr}')
            except BlockingIOError:
                return
        try:
            data = self.conn.recv(1024)
        except BlockingIOError:
            return
        if not data:
            raise ConnectionError('Aria SDK closed the TCP connection')
        self.log(f'RX raw={data!r}')
        # Preserve the established SDK protocol: no unverified CRLF framing.
        message = data.replace(b'\x00', b'').decode('ascii', errors='ignore').strip()
        if not message:
            return
        idx = self.read(self.sdk.Monitoring.GetCurrentStep)
        target = next((i for i in range(max(idx, 0), len(self.steps))
                       if self.steps[i]['type'] == 'WaitForExternalSignal'), None)
        if target is not None and self.steps[target]['parameters'].get('AWAITED_SIGNAL_TYPE') != 'TCP':
            target = None
        self.checkpoint += 1
        checkpoint = dict(id=self.checkpoint, target=target)
        self.pending.append(checkpoint)
        self.log(f'checkpoint={self.checkpoint} target={target} message={message!r}')
        self.send_event('signal', checkpoint=self.checkpoint, message=message)

    def tcp_send_ok(self, checkpoint):
        if self.conn is None:
            raise ConnectionError('No TCP peer for OK')
        self.log(f'TX checkpoint={checkpoint} raw={b"OK\r\n"!r}')
        try:
            self.conn.settimeout(1.0)
            self.conn.sendall(b'OK\r\n')
        finally:
            self.conn.setblocking(False)
        self.log(f'TX completed checkpoint={checkpoint}')

    def command(self, command):
        if command.get('run_id') != self.run_id:
            raise ValueError('Command belongs to a different run')
        name = command['command']
        if name == 'cancel':
            self.begin_stop('cancelled')
        elif self.state == 'stopping':
            return
        elif name == 'start':
            self.start(command)
        elif name in ('pause', 'resume'):
            self.paused = name == 'pause'
            if self.state == 'running' and self.settings.get('enable_device_pause', False):
                paused = self.read(self.sdk.Monitoring.IsSequencePaused)
                if paused != self.paused:
                    method = self.sdk.Monitoring.PauseSequence if self.paused else self.sdk.Monitoring.ResumeSequenceExecution
                    self.check(method(), name)
        elif name == 'ack':
            if self.state != 'running' or not self.pending or self.ack is not None:
                raise ValueError('No checkpoint awaiting an acknowledgement')
            if command.get('checkpoint') != self.pending[0]['id']:
                raise ValueError('Stale or out-of-order checkpoint acknowledgement')
            self.ack = self.pending[0]
        else:
            raise ValueError(f'Unknown command: {name}')

    def async_errors(self):
        # A bounded drain keeps commands responsive even if the SDK floods errors.
        for _ in range(100):
            if not self.sdk.Error.HasAsyncError():
                break
            found, error = self.sdk.Error.TryGetNextAsyncError()
            if not found:
                break
            message = self.sdk.Error.GetErrorMessage(error)
            severity = enum_name(self.sdk.Error.GetErrorSeverity(error))
            self.log(f'asynchronous SDK {severity}: {message}')
            if severity == 'Error':
                raise RuntimeError(f'Asynchronous SDK error: {message}')

    def tick(self):
        if self.state == 'stopping':
            if not self.read(self.sdk.Monitoring.IsSequenceRunning):
                self.finish(self.stop_event, True, self.stop_reason)
            elif time.monotonic() >= self.stop_deadline:
                self.finish('error', False, f'{self.stop_reason}; SDK stop timeout')
            return
        if self.state not in ('starting', 'running'):
            return
        self.async_errors()
        running = self.read(self.sdk.Monitoring.IsSequenceRunning)
        if self.state == 'starting':
            if running:
                self.state = 'running'
                self.send_event('started', wait_count=self.wait_count, configuration=self.configuration)
            elif self.read(self.sdk.Monitoring.HasSequenceEnded):
                self.send_event('started', wait_count=self.wait_count, configuration=self.configuration)
                self.finish('finished', True)
                return
            elif time.monotonic() >= self.start_deadline:
                raise TimeoutError('Aria sequence did not start within 60 seconds')
            else:
                return
        if not running or self.read(self.sdk.Monitoring.HasSequenceEnded):
            if running:
                # HasSequenceEnded may precede the final running-state update.
                return
            self.finish('finished', True)
            return
        idx = self.read(self.sdk.Monitoring.GetCurrentStep)
        if self.settings.get('enable_device_pause', False):
            sdk_paused = self.read(self.sdk.Monitoring.IsSequencePaused)
            if sdk_paused != self.paused:
                method = self.sdk.Monitoring.PauseSequence if self.paused else self.sdk.Monitoring.ResumeSequenceExecution
                self.check(method(), 'synchronize pause state')
        if idx != self.last_step:
            self.log(f'step changed {self.last_step} -> {idx}')
            self.last_step = idx
            self.step_started = time.monotonic()
        self.accept_and_poll()
        if self.ack is not None and not self.paused:
            checkpoint = self.ack
            self.tcp_send_ok(checkpoint['id'])
            self.pending.popleft()
            self.ack = None
            self.retry = dict(**checkpoint, at=time.monotonic() + self.RETRY_INTERVAL)
            self.send_event('ack_sent', checkpoint=checkpoint['id'])
        if self.retry is not None:
            target = self.retry['target']
            if target is None or idx > target:
                self.retry = None
            elif idx == target and not self.paused and time.monotonic() >= self.retry['at']:
                self.tcp_send_ok(self.retry['id'])
                self.retry['at'] = time.monotonic() + self.RETRY_INTERVAL
        if time.monotonic() >= self.next_status:
            self.publish_status(idx)
            self.next_status = time.monotonic() + 0.5

    def publish_status(self, idx):
        if idx == self.sdk.Monitoring.GetPrefillStepNumber():
            info = dict(type='Prefill', parameters={}, estimated_duration=0)
            progress = self.read(self.sdk.Monitoring.GetPrefillAndPreloadProgress)
        elif idx == self.sdk.Monitoring.GetPreloadStepNumber():
            info = dict(type='Preload', parameters={}, estimated_duration=0)
            progress = self.read(self.sdk.Monitoring.GetPrefillAndPreloadProgress)
        else:
            if not 0 <= idx < len(self.steps):
                raise RuntimeError(f'Invalid current Aria step: {idx}')
            info = self.steps[idx]
            progress = self.read(self.sdk.Monitoring.GetProgress, idx)
        self.send_event('status', step_index=idx, step_count=len(self.steps),
                        step_elapsed=time.monotonic() - self.step_started,
                        progress=progress, pressure=self.read(self.sdk.FlowControl.GetMeasuredPressure),
                        flow_rate=self.read(self.sdk.FlowControl.GetMeasuredFlowRate), **info)

    def begin_stop(self, event='cancelled', reason=''):
        if self.state in ('stopping', 'terminal'):
            return
        self.stop_event, self.stop_reason = event, reason
        self.ack = self.retry = None
        self.pending.clear()
        self.state = 'stopping'
        self.stop_deadline = time.monotonic() + self.STOP_TIMEOUT
        if self.read(self.sdk.Monitoring.IsSequenceRunning):
            self.check(self.sdk.Monitoring.Cancel(), 'cancel sequence')

    def finish(self, event, confirmed, message=''):
        self.close_sockets()
        self.state = 'terminal'
        self.exit_code = 0 if confirmed and event != 'error' else 1
        self.send_event(event, cleanup_confirmed=confirmed, message=message)

    def close_sockets(self):
        if self.conn is not None:
            try:
                self.conn.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            self.conn.close()
            self.conn = None
        if self.server is not None:
            self.server.close()
            self.server = None

    def run(self):
        self.send_event('ready')
        try:
            while self.state != 'terminal':
                try:
                    for _ in range(100):
                        try:
                            command = self.commands.get_nowait()
                        except queue.Empty:
                            break
                        if command is None:
                            self.begin_stop('cancelled', 'parent input closed')
                        else:
                            self.command(command)
                    self.tick()
                except Exception as exc:
                    self.log(traceback.format_exc())
                    if self.state == 'stopping':
                        self.finish('error', False, str(exc))
                    else:
                        try:
                            self.begin_stop('error', str(exc))
                        except Exception as cleanup_exc:
                            self.finish('error', False, f'{exc}; cleanup failed: {cleanup_exc}')
                time.sleep(0.05)
        finally:
            self.close_sockets()
        return self.exit_code


def main(sdk=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    protocol = sys.stdout
    # Capture the original stdout for protocol output before importing the SDK.
    sys.stdout = sys.stderr

    def emit(event):
        protocol.write(json.dumps(event, ensure_ascii=True, allow_nan=False) + '\n')
        protocol.flush()

    try:
        if sdk is None:
            sdk = importlib.import_module('Aria.SDK')
            from System import Console
            from System.Text import UTF8Encoding
            Console.OutputEncoding = UTF8Encoding(False)
            Console.SetOut(Console.Error)
        commands = queue.Queue()

        def read_commands():
            try:
                for line in sys.stdin:
                    try:
                        commands.put(json.loads(line))
                    except (ValueError, TypeError):
                        commands.put(dict(command='invalid', run_id=args.run_id))
            finally:
                commands.put(None)

        threading.Thread(target=read_commands, name='aria-commands', daemon=True).start()
        return Worker(sdk, args.run_id, emit, commands).run()
    except Exception as exc:
        traceback.print_exc(file=sys.stderr)
        emit(dict(event='error', run_id=args.run_id, pid=os.getpid(),
                  cleanup_confirmed=False, message=str(exc)))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
