import time
import math
import os
import sys
import json
import subprocess
from datetime import datetime

class SoakMyBed:
    def __init__(self, config):
        self.printer = config.get_printer()
        self.gcode = self.printer.lookup_object('gcode')
        
        self.gcode.register_command('SOAK_MY_BED', self.cmd_SOAK_MY_BED)
        self.gcode.register_command('ABORT_SOAK', self.cmd_ABORT_SOAK)
        self.gcode.register_command('_SOAK_AFTER_FIRST', self.cmd__SOAK_AFTER_FIRST)
        self.gcode.register_command('_SOAK_LOOP_EVAL', self.cmd__SOAK_LOOP_EVAL)
        self.gcode.register_command('_SOAK_LOOP_WAIT', self.cmd__SOAK_LOOP_WAIT)
        
        self.temp = 0.0
        self.duration_sec = 0.0
        self.heater = ""
        self.sensor_name = ""
        self.mesh_cmd = ""
        self.script_start_time = 0.0
        self.mesh_start_time = 0.0
        self.soak_start_time = None
        self.is_heating = False
        self.is_running = False
        self.scan_count = 0 
        
        home_dir = os.path.expanduser("~")
        default_save_dir = os.path.join(home_dir, "printer_data", "config", "soak_data")
        default_plot_script = os.path.join(home_dir, "soak-my-bed", "scripts", "plotter.py")
        
        self.save_dir = config.get('save_dir', default_save_dir)
        self.plot_script_path = config.get('plot_script_path', default_plot_script)
        self.klipper_python = sys.executable 
        self.default_mesh_cmd = config.get('mesh_command', 'BED_MESH_CALIBRATE')
        
        raw_extra = config.get('extra_sensors', '')
        self.extra_sensors = [s.strip() for s in raw_extra.split(',') if s.strip()]
        
        self.json_path = ""
        self.gcode.respond_info(f"SoakMyBed v1.0.4 initialized with {len(self.extra_sensors)} extra sensors.")

    def cmd_SOAK_MY_BED(self, gcmd):
        if self.is_running:
            self.gcode.respond_info("A soak is already in progress.")
            return

        self.temp = gcmd.get_float('TEMPERATURE', 60.0)
        self.duration_sec = gcmd.get_float('DURATION', 10.0) * 60.0
        self.heater = gcmd.get('HEATER', 'heater_bed')
        self.scan_count = 0 
        
        raw_mesh_cmd = gcmd.get('MESH_COMMAND', self.default_mesh_cmd).strip('"\'')
        if "PROFILE=" not in raw_mesh_cmd.upper():
            self.mesh_cmd = f"{raw_mesh_cmd} PROFILE=soak"
        else:
            self.mesh_cmd = raw_mesh_cmd

        if self.heater in ['heater_bed', 'extruder']:
            self.sensor_name = self.heater
        else:
            self.sensor_name = f"heater_generic {self.heater}"

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        duration_min = int(self.duration_sec / 60)
        filename = f"{timestamp}_{int(self.temp)}C_{duration_min}m.json"
        self.json_path = os.path.join(self.save_dir, filename)

        try:
            os.makedirs(self.save_dir, exist_ok=True)
            with open(self.json_path, "w") as f:
                json.dump([], f) 
            self.gcode.respond_info(f"Session started: {filename}")
        except Exception as e:
            self.gcode.respond_info(f"Storage Error: {e}")
            return

        self.script_start_time = time.time()
        self.soak_start_time = None
        self.is_heating = True
        self.is_running = True

        self.gcode.respond_info("Phase 1: Baseline cold mesh...")
        self.mesh_start_time = time.time()
        self.gcode.run_script_from_command(f"{self.mesh_cmd}\n_SOAK_AFTER_FIRST")

    def cmd_ABORT_SOAK(self, gcmd):
        if not self.is_running: return
        self.is_running = False
        self.is_heating = False
        self.gcode.respond_info("SOAK ABORTED. Generating partial plots...")
        self.run_plotter()
        self.gcode.run_script_from_command(f"SET_HEATER_TEMPERATURE HEATER={self.heater} TARGET=0")

    def cmd__SOAK_AFTER_FIRST(self, gcmd):
        if not self.is_running: return
        self.gcode.respond_info(f"Phase 2: Heating {self.heater} to {self.temp}C...")
        self.gcode.run_script_from_command(f"SET_HEATER_TEMPERATURE HEATER={self.heater} TARGET={self.temp}\n_SOAK_LOOP_EVAL")

    def cmd__SOAK_LOOP_EVAL(self, gcmd):
        if not self.is_running: return
        try:
            sensor_obj = self.printer.lookup_object(self.sensor_name)
            status = sensor_obj.get_status(self.printer.get_reactor().monotonic())
            current_temp = status.get('temperature', 0.0)
        except: 
            self.is_running = False
            return

        self.scan_count += 1
        elapsed_total = int(time.time() - self.script_start_time)
        
        log_msg = f"Elapsed time: {elapsed_total}s\n"
        log_msg += f"Scan n° {self.scan_count}\n"
        log_msg += f"Temperature: {current_temp:.1f}/{self.temp:.1f}°C"
        
        if self.is_heating:
            if current_temp >= (self.temp - 0.5):
                self.is_heating = False
                self.soak_start_time = time.time()
                log_msg += "\nTarget reached! Soak timer started."
        else:
            elapsed_soak = time.time() - self.soak_start_time
            remaining = int(self.duration_sec - elapsed_soak)
            if remaining <= 0:
                self.is_running = False
                self.gcode.respond_info("SOAK COMPLETE!")
                self.run_plotter()
                self.gcode.run_script_from_command(f"SET_HEATER_TEMPERATURE HEATER={self.heater} TARGET=0")
                return 
            log_msg += f"\nTime remaining: {remaining}s"

        self.gcode.respond_info(log_msg)
        self.mesh_start_time = time.time()
        self.gcode.run_script_from_command(f"{self.mesh_cmd}\n_SOAK_LOOP_WAIT")

    def run_plotter(self):
        try:
            subprocess.Popen([self.klipper_python, self.plot_script_path, self.json_path])
            self.gcode.respond_info(f"Plotting started. Files will be saved in: {self.save_dir}")
        except Exception as e:
            self.gcode.respond_info(f"Plotting Error: {e}")

    def cmd__SOAK_LOOP_WAIT(self, gcmd):
        if not self.is_running: return
        reactor = self.printer.get_reactor()
        eventtime = reactor.monotonic()
        try:
            bed_mesh = self.printer.lookup_object('bed_mesh', None)
            sensor_obj = self.printer.lookup_object(self.sensor_name)
            current_temp = sensor_obj.get_status(eventtime).get('temperature', 0.0)
            
            extra_temps = {}
            for s_name in self.extra_sensors:
                try:
                    s_obj = self.printer.lookup_object(s_name)
                    extra_temps[s_name] = s_obj.get_status(eventtime).get('temperature', 0.0)
                except:
                    pass

            if bed_mesh is not None:
                mesh_status = bed_mesh.get_status(eventtime)
                matrix = mesh_status.get('probed_matrix') or mesh_status.get('mesh_matrix', [[]])
                mesh_min = mesh_status.get('mesh_min', [0.0, 0.0])
                mesh_max = mesh_status.get('mesh_max', [300.0, 300.0])
                
                with open(self.json_path, "r") as f: data = json.load(f)
                data.append({
                    "time": time.time() - self.script_start_time, 
                    "temp": current_temp, 
                    "extra_temps": extra_temps,
                    "matrix": matrix,
                    "mesh_min": mesh_min,
                    "mesh_max": mesh_max,
                    "primary_sensor": self.heater
                })
                with open(self.json_path, "w") as f: json.dump(data, f)
        except: pass
        
        mesh_duration = time.time() - self.mesh_start_time
        wait_interval = max(1.0, (math.ceil((mesh_duration + 3.0) / 5.0) * 5.0) - mesh_duration)
        reactor.register_timer(self._trigger_next_eval, eventtime + wait_interval)

    def _trigger_next_eval(self, eventtime):
        if self.is_running:
            self.gcode.run_script_from_command("_SOAK_LOOP_EVAL")
        return self.printer.get_reactor().NEVER

def load_config(config):
    return SoakMyBed(config)
