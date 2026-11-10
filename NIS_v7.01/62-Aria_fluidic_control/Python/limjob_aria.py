from __future__ import annotations
from dataclasses import dataclass, field
from collections import deque
from pathlib import Path
from typing import Deque, Optional
import html
import json
import os
import queue
import subprocess
import sys
import threading
import time
import uuid

import limjob
import numpy as np

@dataclass
class AriaPlotter:
    color_scheme_name: str = "light"

    start_time: Optional[float] = None
    data_time: Deque[float] = field(default_factory=deque)
    data_pressure: Deque[float] = field(default_factory=deque)
    data_flow_rate: Deque[float] = field(default_factory=deque)
    pressure_range: Optional[tuple[float, float]] = None
    flow_range: Optional[tuple[float, float]] = None

    PLOT_WINDOW_SEC: int = 30    

    def start_new_block(self):
        self.data_time.append(np.nan)
        self.data_pressure.append(np.nan)
        self.data_flow_rate.append(np.nan)
    
    def append_data(self, time: float, pressure: float, flow_rate: float):
        if self.start_time is None:
            self.start_time = time

        time -= self.start_time
        self.data_time.append(time)
        self.data_pressure.append(pressure)
        self.data_flow_rate.append(flow_rate)

        clip_time = time - self.PLOT_WINDOW_SEC
        while len(self.data_time) and (self.data_time[0] < clip_time or np.isnan(self.data_time[0])):
            self.data_time.popleft()
            self.data_pressure.popleft()
            self.data_flow_rate.popleft()

    def plot_to_image(self):
        import matplotlib.pyplot as plt
        import matplotlib.ticker as ticker
        import base64, io
        
        WIDTH_INCH = 5
        HEIGHT_INCH = 3
        DPI_MOD = 2
        DPI_BASE = 96

        def format_time(x, pos):
            secs = int(round(x))
            mins = secs // 60
            hrs = mins // 60
            secs %= 60
            mins %= 60
            if hrs <= 0:
                return f"{mins}:{secs:02d}"
            return f"{hrs}:{mins:02d}:{secs:02d}"

        is_light_scheme = self.color_scheme_name == "light"
        COLOR_BASE = "#fcfcfc" if is_light_scheme else '#444444'
        COLOR_TEXT = "#000000" if is_light_scheme else '#f0f0f0'
        COLOR_PRESSURE = "#4c72b0" if is_light_scheme else '#a1c9f4'
        COLOR_FLOW_RATE ="#dd8452" if is_light_scheme else '#ffb482'
        with plt.rc_context({
            "figure.facecolor": COLOR_BASE,
            "axes.facecolor": COLOR_BASE,
            "text.color": COLOR_TEXT,
            "axes.labelcolor": COLOR_TEXT,
            "xtick.color": COLOR_TEXT,
            "ytick.color": COLOR_TEXT,
            "grid.color": COLOR_TEXT,
            "axes.edgecolor": COLOR_TEXT,
            "font.family": 'sans-serif',
            "font.sans-serif": ['Tahoma'],
            "font.size": 8,
        }):
            fig, ax = plt.subplots(figsize=(WIDTH_INCH, HEIGHT_INCH))
            #print("Plot to image")
            if self.pressure_range is not None:
                ax.set_ylim(self.pressure_range)
            else:
                ax.set_ylim(bottom = min(0, min(self.data_pressure) * 1.1), top = max(self.data_pressure) * 2)
            xrange = (max(0, self.data_time[-1] - self.PLOT_WINDOW_SEC), self.data_time[-1])
            if xrange[1] - xrange[0] < self.PLOT_WINDOW_SEC:
                xrange = (xrange[0], xrange[0] + self.PLOT_WINDOW_SEC)
            xrange_margin = 0.05 * (xrange[1] - xrange[0])
            xrange = (xrange[0] - xrange_margin, xrange[1] + xrange_margin)
            ax.set_xlim(xrange)

            line1, = ax.plot(list(self.data_time), list(self.data_pressure), color=COLOR_PRESSURE, label="Pressure [mbar]", clip_on=False, zorder=10)
            ax.set_xlabel('Time [s]')
            ax.xaxis.set_major_formatter(ticker.FuncFormatter(format_time))
            ax.set_ylabel('Pressure [mbar]')
            ax.grid(True, alpha=0.3)

            ax2 = ax.twinx()
            if self.flow_range is not None:
                #print("Plot to image -> If")
                ax2.set_ylim(self.flow_range)
            else:
                #print("Plot to image -> Else")
                ax2.set_ylim(bottom = min(0, min(self.data_flow_rate) * 1.1), top = max(self.data_flow_rate) * 1.1)
            line2, = ax2.plot(list(self.data_time), list(self.data_flow_rate), color=COLOR_FLOW_RATE, linestyle='--', label='Flow rate [\u03bcl/min]', clip_on=False, zorder=10)
            ax2.set_ylabel('Flow rate [\u03bcl/min]')

            ax.legend(handles=[line1, line2], loc="upper center", bbox_to_anchor=(0.5, -0.22), ncol=2, frameon=False)
            
            fig.subplots_adjust(left=0.15, right=0.85, bottom=0.30, top=0.95)

            buffer = io.BytesIO()
            #print("Buffer: ", buffer)
            fig.savefig(buffer, dpi=DPI_MOD*DPI_BASE)
            
            plt.close(fig)

        b64 = base64.b64encode(buffer.getvalue())
        return f'<img src="data:image/png;base64,{b64.decode("ascii")}" style="width:{WIDTH_INCH*DPI_BASE}px; height:{HEIGHT_INCH*DPI_BASE}px;"/>'

@dataclass
class AriaSettings:
    enable_prefill: bool|None = None
    enable_zero_pressure_mode: bool|None = None
    prefill_and_preload_flow_rate: str|None = None
    enable_simulated_instrument: bool|None = None
    plot_color_scheme_name: str = "light"
    enable_device_pause: bool|None = None

def _create_aria_settings(src_settings: dict|None) -> AriaSettings:
    aria_settings = AriaSettings()
    if src_settings is not None:
        if 'enable_prefill' in src_settings:
            if not isinstance(src_settings['enable_prefill'], bool):
                raise TypeError("enable_prefill must be bool or None")
            aria_settings.enable_prefill = src_settings['enable_prefill']

        if 'enable_zero_pressure_mode' in src_settings:
            if not isinstance(src_settings['enable_zero_pressure_mode'], bool):
                raise TypeError("enable_zero_pressure_mode must be bool or None")
            aria_settings.enable_zero_pressure_mode = src_settings['enable_zero_pressure_mode']

        if 'prefill_and_preload_flow_rate' in src_settings:
            if not isinstance(src_settings['prefill_and_preload_flow_rate'], str):
                raise TypeError("prefill_and_preload_flow_rate must be str or None")
            aria_settings.prefill_and_preload_flow_rate = src_settings['prefill_and_preload_flow_rate']

        if 'enable_simulated_instrument' in src_settings:
            if not isinstance(src_settings['enable_simulated_instrument'], bool):
                raise TypeError("enable_simulated_instrument must be bool or None")
            aria_settings.enable_simulated_instrument = src_settings['enable_simulated_instrument']

        if 'plot_color_scheme_name' in src_settings:
            if not isinstance(src_settings['plot_color_scheme_name'], str):
                raise TypeError("plot_color_scheme_name must be str or None")
            aria_settings.plot_color_scheme_name = src_settings['plot_color_scheme_name']

        if 'enable_device_pause' in src_settings:
            if not isinstance(src_settings['enable_device_pause'], bool):
                raise TypeError("enable_device_pause must be bool or None")
            aria_settings.enable_device_pause = src_settings['enable_device_pause']

    return aria_settings


class AriaController:
    READY_TIMEOUT = 30.0
    START_TIMEOUT = 60.0
    STOP_TIMEOUT = 35.0
    ACK_TIMEOUT = 30.0
    EXIT_TIMEOUT = 5.0

    def __init__(self, settings=None):
        self.settings = _create_aria_settings(settings)
        self.settings_dict = dict(settings or {})
        self.plotter = AriaPlotter(color_scheme_name=self.settings.plot_color_scheme_name)
        self.run_id = uuid.uuid4().hex
        self.process = None
        self.events = queue.Queue()
        self.deferred = deque()
        self.status = None
        self.configuration = None
        self.status_lock = threading.Lock()
        self.threads = []
        self.last_message = None
        self.checkpoint = None
        self.terminal = None
        self.closed = False
        self.unsafe = False
        self.pause_sent = None
        self.next_render = 0.0
        self.logs = deque(maxlen=20)

    @staticmethod
    def worker_command():
        module = Path(__file__).resolve()
        # Installed as Python/Lib/site-packages/limjob_aria.py.
        executable = module.parents[2] / 'python.exe'
        worker = module.with_name('limjob_aria_worker.py')
        if not executable.is_file():
            raise limjob.JobPyScriptError(f"Bundled Aria Python not found: {executable}")
        if not worker.is_file():
            raise limjob.JobPyScriptError(f"Aria worker not found: {worker}")
        return [str(executable), '-u', str(worker)]

    def launch(self):
        command = self.worker_command() + ['--run-id', self.run_id]
        self.process = subprocess.Popen(
            command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='strict',
            bufsize=1, shell=False,
            env=dict(os.environ, PYTHONIOENCODING='utf-8'),
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        print(f"[Aria {self.run_id}] worker PID={self.process.pid}", flush=True)
        for name, target in (('aria-events', self._read_events), ('aria-log', self._read_log)):
            thread = threading.Thread(target=target, name=name, daemon=True)
            self.threads.append(thread)
            thread.start()

    def _read_events(self):
        try:
            for line in self.process.stdout:
                event = json.loads(line)
                if not isinstance(event, dict) or event.get('run_id') != self.run_id:
                    raise ValueError('Aria worker protocol run mismatch')
                if event.get('event') == 'status':
                    with self.status_lock:
                        self.status = event
                else:
                    self.events.put(event)
                    print("_read_events - Event: ", event)
        except Exception as exc:
            self.events.put(dict(event='protocol_error', message=str(exc)))
        finally:
            self.events.put(dict(event='eof'))

    def _read_log(self):
        try:
            for line in self.process.stderr:
                self.logs.append(line.rstrip())
                print(line.rstrip(), flush=True)
        except (OSError, UnicodeError, ValueError) as exc:
            self.logs.append(str(exc))

    def send(self, command, **values):
        if self.process is None or self.process.poll() is not None:
            raise limjob.JobPyScriptError('Aria worker is not running')
        try:
            self.process.stdin.write(json.dumps(
                dict(command=command, run_id=self.run_id, **values), ensure_ascii=True) + '\n')
            self.process.stdin.flush()
            print("send - command: ", command)
        except (OSError, ValueError) as exc:
            raise limjob.JobPyScriptError(f"Cannot send Aria command {command}: {exc}") from exc

    def snapshot(self):
        with self.status_lock:
            return self.status

    def _context(self, ctx):
        if ctx.shouldAbort:
            self.close()
            return False
        paused = bool(ctx.isPaused)
        if paused != self.pause_sent:
            self.send('pause' if paused else 'resume')
            self.pause_sent = paused
        return True

    def _event(self, timeout=0.05):
        try:
            event = self.events.get(timeout=timeout)
        except queue.Empty:
            return None
        kind = event.get('event')
        if kind in ('finished', 'cancelled', 'error'):
            self.terminal = event
            if not event.get('cleanup_confirmed', False):
                self.unsafe = True
            if kind == 'error':
                raise limjob.JobPyScriptError(event.get('message', 'Aria worker failed'))
        elif kind in ('eof', 'protocol_error'):
            if self.terminal is None:
                self.unsafe = True
                details = event.get('message') or '\n'.join(self.logs)
                raise limjob.JobPyScriptError(f"Aria worker stopped without confirmed cleanup: {details}")
        return event

    def _await(self, wanted, timeout, ctx, Job=None):
        deadline = time.monotonic() + timeout if timeout is not None else None
        last_tick = time.monotonic()
        while True:
            print("_await - While")
            now = time.monotonic()
            if deadline is not None and ctx.isPaused:
                deadline += now - last_tick
            last_tick = now
            if not self._context(ctx):
                return None
            if Job is not None:
                self.render(Job, ctx)
            if 'signal' in wanted and self.deferred:
                event = self.deferred.popleft()
            else:
                event = self._event()
            if event is not None:
                if event['event'] in wanted:
                    return event
                if event['event'] == 'signal':
                    self.deferred.append(event)
                    continue
                if event['event'] in ('finished', 'cancelled'):
                    return event
                raise limjob.JobPyScriptError(f"Unexpected Aria worker event: {event['event']}")
            if deadline is not None and time.monotonic() >= deadline:
                raise limjob.JobPyScriptError(f"Aria worker timeout waiting for {', '.join(wanted)}")

    def start(self, sequence_json, ctx, Job):
        self.launch()
        # Do not send pause/resume until ready: SDK import may still be running.
        deadline = time.monotonic() + self.READY_TIMEOUT
        while True:
            if ctx.shouldAbort:
                self.close()
                return None
            event = self._event()
            if event is not None:
                if event['event'] != 'ready':
                    raise limjob.JobPyScriptError('Aria worker did not report ready')
                break
            if time.monotonic() >= deadline:
                raise limjob.JobPyScriptError('Aria worker readiness timeout')
        self.send('start', sequence_json=sequence_json, settings=self.settings_dict)
        event = self._await({'started'}, self.START_TIMEOUT, ctx, Job)
        if event is None:
            return None
        if event['event'] != 'started':
            raise limjob.JobPyScriptError('Aria worker ended before start confirmation')
        self.configuration = event.get('configuration')
        return event['wait_count']

    def wait_for_signal(self, Job, ctx):
        self.plotter.start_new_block()
        event = self._await({'signal'}, None, ctx, Job)
        if event is not None and event['event'] == 'signal':
            print("wait_for_signal - event: ", event)
            self.last_message = event['message']
            self.checkpoint = event['checkpoint']
            return True
        self.last_message = None
        self.close()
        return False

    def acknowledge(self, Job, ctx):
        if not self._context(ctx):
            return False
        if self.checkpoint is None:
            raise limjob.JobPyScriptError('No Aria checkpoint to acknowledge')
        checkpoint = self.checkpoint
        self.send('ack', checkpoint=checkpoint)
        event = self._await({'ack_sent'}, self.ACK_TIMEOUT, ctx, Job)
        if event is None:
            return False
        if event['event'] != 'ack_sent' or event.get('checkpoint') != checkpoint:
            raise limjob.JobPyScriptError('Aria acknowledgement did not match the checkpoint')
        self.checkpoint = None
        return True

    def close(self):
        print("close")
        if self.closed:
            if self.unsafe:
                raise limjob.JobPyScriptError('Previous Aria cleanup was not confirmed; restart requires operator recovery')
            return
        failure = None
        try:
            if self.process is None:
                return
            # A terminal event can already be queued while the Job body executes.
            while self.terminal is None:
                try:
                    event = self._event(timeout=0)
                except limjob.JobPyScriptError as exc:
                    failure = exc
                    if self.terminal is not None:
                        break
                    raise
                if event is None:
                    break
            if self.terminal is None:
                self.send('cancel')
                deadline = time.monotonic() + self.STOP_TIMEOUT
                while self.terminal is None:
                    try:
                        self._event()
                    except limjob.JobPyScriptError as exc:
                        failure = exc
                        if self.terminal is None:
                            raise
                    if time.monotonic() >= deadline:
                        raise limjob.JobPyScriptError('Aria worker cleanup timeout')
            self.process.wait(timeout=self.EXIT_TIMEOUT)
            if not self.terminal.get('cleanup_confirmed', False):
                self.unsafe = True
            if self.process.returncode != 0 and self.terminal['event'] != 'error':
                self.unsafe = True
                raise limjob.JobPyScriptError(f"Aria worker exited with code {self.process.returncode}")
        except Exception as exc:
            failure = exc
            self.unsafe = True
        finally:
            if self.process is not None:
                if self.process.poll() is None:
                    self.unsafe = True
                    self.process.kill()
                    self.process.wait(timeout=self.EXIT_TIMEOUT)
                # Readers drain to EOF before their streams are closed.
                for thread in self.threads:
                    thread.join(timeout=self.EXIT_TIMEOUT)
                for stream in (self.process.stdin, self.process.stdout, self.process.stderr):
                    if stream is not None:
                        stream.close()
            self.closed = True
            self.checkpoint = None
            self.last_message = None
        if failure is not None:
            raise limjob.JobPyScriptError(f"Aria run failed: {failure}") from failure
        if self.unsafe:
            raise limjob.JobPyScriptError('Aria cleanup was not confirmed; new starts are blocked')

    def render(self, Job, ctx):
        status = self.snapshot()
        now = time.monotonic()
        if status is None or now < self.next_render:
            return
        self.next_render = now + 0.5
        self.plotter.append_data(now, status['pressure'], status['flow_rate'])
        names = {'TimeInjection': 'Time Injection', 'VolumeInjection': 'Volume Injection',
                 'WaitForUser': 'Wait for user', 'WaitForExternalSignal': 'Wait for external signal',
                 'SendExternalSignal': 'Send external signal'}
        step_name = names.get(status['type'], status['type'])
        labels = {'INPUT_RESERVOIR': 'Reservoir', 'OUTPUT_DESTINATION': 'Destination',
                  'FLOWRATE': 'Flow rate [µl/min]', 'VOLUME': 'Volume [µl]',
                  'DURATION': 'Timeout', 'SIGNAL_MESSAGE': 'Message',
                  'AWAITED_SIGNAL_TYPE': 'Signal', 'BACKTRACK': 'Backtrack'}
        rows = []
        for key, value in status['parameters'].items():
            if key == 'DURATION':
                value = _seconds_to_text(int(value))
            elif key == 'BACKTRACK':
                value = f"{value} ({'starts listening after last signal' if value else 'starts listening after step starts'})"
            rows.append(f'<tr><td>{labels.get(key, key)}:</td><td>{html.escape(str(value))}</td></tr>')
        elapsed = status['step_elapsed']
        estimated = status['estimated_duration']
        progress = status['progress']
        if estimated <= 0 and 0 < progress < 100:
            estimated = elapsed / progress * 100
        step_num = status['step_index'] + 1 if status['step_index'] >= 0 else '?'
        pause_html = ''
        if ctx.isPaused:
            aria_state = ('ARIA is paused' if self.settings.enable_device_pause else
                          'ARIA will continue and stop at the next checkpoint (TCP communication step).')
            pause_html = f'<div style="background:#c62828;color:white;padding:0.5em">JOBs are paused<br>{aria_state}</div>'
        Job.ProgressHtml = f"""
<div style="margin:0.5em">
    <h1>Aria sequence running</h1>{pause_html}
    <p style="font-size:1.5em">[{step_num}/{status['step_count']}] <b>{html.escape(step_name)}</b></p>
    <div style="display:flex;gap:2em">
        <div style="flex-shrink:0">{self.plotter.plot_to_image()}</div>
        <div><b>State</b><br>
            <table><tr><td>Pressure:</td><td>{status['pressure']:5.2f} mbar</td></tr>
            <tr><td>Flow rate:</td><td>{status['flow_rate']:5.2f} µl/min</td></tr></table>
            <br><b>Step: {html.escape(step_name)}</b>
            <div style="min-height:8em"><table>{''.join(rows)}</table></div>
            {_progress_div(progress, int(elapsed), int(estimated))}
        </div>
    </div>
</div>
"""


class AriaLoop(limjob.CountLoop):
    def __init__(self, controller, count):
        super().__init__(count)
        self.controller = controller


_controller = None
_init_lock = threading.Lock()


def _init_loop(Job, ctx, sequence_path=None, sequence_json=None, settings=None):
    with _init_lock:
        return _start_loop(Job, ctx, sequence_path, sequence_json, settings)


def _start_loop(Job, ctx, sequence_path, sequence_json, settings):
    global _controller
    if _controller is not None:
        _controller.close()
    if 'aria_sdk' in sys.modules or 'Aria.SDK' in sys.modules:
        raise limjob.JobPyScriptError('Restart NIS-Elements once to unload the previously used in-process Aria SDK')
    if ctx.shouldAbort:
        raise limjob.JobPyScriptError('Aria start was aborted')
    if sequence_path is not None:
        with open(sequence_path, encoding='utf-8-sig') as sequence_file:
            sequence_json = sequence_file.read()
    if sequence_json is None:
        raise ValueError('Aria sequence file or JSON is required')
    json.loads(sequence_json)
    controller = AriaController(settings)
    _controller = controller
    Job.ProgressHtml = '<h1>Aria sequence starting</h1>'
    try:
        count = controller.start(sequence_json, ctx, Job)
        return AriaLoop(controller, count if count is not None else 0)
    except BaseException:
        try:
            controller.close()
        except Exception as cleanup_error:
            print(f"[Aria {controller.run_id}] {cleanup_error}", flush=True)
        raise


def loop_init_file(Job: limjob.JobParam, ctx: limjob.RunContext, sequence_path: str, settings: dict|None = None) -> limjob.Loop:
    return _init_loop(Job, ctx, sequence_path=sequence_path, settings=settings)


def loop_init_json(Job: limjob.JobParam, ctx: limjob.RunContext, sequence_json: str, settings: dict|None = None) -> limjob.Loop:
    return _init_loop(Job, ctx, sequence_json=sequence_json, settings=settings)


def _cleanup_on_error(controller):
    try:
        controller.close()
    except Exception as exc:
        print(f"[Aria {controller.run_id}] {exc}", flush=True)


def loop_condition(loop: limjob.Loop, Job: limjob.JobParam, ctx: limjob.RunContext) -> bool:
    controller = loop.controller
    if controller.closed:
        return False
    try:
        if not controller.wait_for_signal(Job, ctx):
            return False
        if not loop.check(ctx):
            raise limjob.JobPyScriptError('Aria emitted more checkpoints than the configured loop count')
        return True
    except BaseException:
        _cleanup_on_error(controller)
        raise


def loop_step(loop: limjob.Loop, Job: limjob.JobParam, ctx: limjob.RunContext) -> limjob.Loop:
    try:
        if loop.controller.acknowledge(Job, ctx):
            return loop.next(ctx)
        return loop
    except BaseException:
        _cleanup_on_error(loop.controller)
        raise


def last_tcp_message() -> str|None:
    return _controller.last_message if _controller is not None else None


def current_step_type():
    status = _controller.snapshot() if _controller is not None else None
    if status is None:
        print('Aria status is not available', flush=True)
        return
    print(f"Aria worker step index: {status['step_index']}; type: {status['type']}", flush=True)


# auxilary functions
# ==================================================

def _seconds_to_text(secs: int):
    mins = secs // 60
    hrs = mins // 60
    secs %= 60
    mins %= 60
    return f"{hrs:02d}:{mins:02d}:{secs:02d}"

def _progress_div(progress: float, current_duration_sec: int, estimated_duration_sec: int):
    return f"""
<div style="padding:0.5em; width:100%">
    <div style="height:2em; border-radius:1em; overflow:hidden; position:relative;">
        <div style="height:100%; width:100%; background:#275929;">
            <div style="height:100%; width:{progress}%; background:#4caf50; display: flex; justify-content: center;"></div>
        </div>
        <span style="position:absolute; inset:0; font-size:1em; display: flex; align-items:center; justify-content:center;">{round(progress, 2)}%</span>
    </div>
    <div style="display:flex; justify-content:space-between; font-size:1em; margin-top:4px;">
        <span>Step time / estimated:</span>
        <span>{_seconds_to_text(current_duration_sec)} / {_seconds_to_text(estimated_duration_sec)}</span>
    </div>
</div>
"""

