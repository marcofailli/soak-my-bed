import time
import math
import os
import json
import subprocess
from datetime import datetime

class SoakMyBed:
    def __init__(self, config):
        self.printer = config.get_printer()
        self.gcode = self.printer.lookup_object('gcode')
        
        # Comandi Utente
        self.gcode.register_command('SOAK_MY_BED', self.cmd_SOAK_MY_BED)
        self.gcode.register_command('ABORT_SOAK', self.cmd_ABORT_SOAK)
        
        # Comandi Interni
        self.gcode.register_command('_SOAK_AFTER_FIRST', self.cmd__SOAK_AFTER_FIRST)
        self.gcode.register_command('_SOAK_LOOP_EVAL', self.cmd__SOAK_LOOP_EVAL)
        self.gcode.register_command('_SOAK_LOOP_WAIT', self.cmd__SOAK_LOOP_WAIT)
        
        # Variabili di stato
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
        
        # Percorsi base
        self.save_dir = "/home/pi/printer_data/config/soak_data"
        self.plot_script_path = "/home/pi/soak-my-bed/scripts/plotter.py"
        self.klipper_python = "/home/pi/klippy-env/bin/python"
        self.json_path = ""

    def cmd_SOAK_MY_BED(self, gcmd):
        if self.is_running:
            self.gcode.respond_info("A SOAK procedure is already running! Use ABORT_SOAK to stop it.")
            return

        self.temp = gcmd.get_float('TEMPERATURE', 60.0)
        self.duration_sec = gcmd.get_float('DURATION', 10.0) * 60.0
        self.heater = gcmd.get('HEATER', 'heater_bed')
        
        raw_mesh_cmd = gcmd.get('MESH_COMMAND', 'BED_MESH_CALIBRATE METHOD=rapid_scan')
        raw_mesh_cmd = raw_mesh_cmd.strip('"\'')
        
        if "PROFILE=" not in raw_mesh_cmd.upper():
            self.mesh_cmd = f"{raw_mesh_cmd} PROFILE=soak"
        else:
            self.mesh_cmd = raw_mesh_cmd

        if self.heater in ['heater_bed', 'extruder']:
            self.sensor_name = self.heater
        else:
            self.sensor_name = f"heater_generic {self.heater}"

        # Creazione file JSON con Data e Ora
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.json_path = os.path.join(self.save_dir, f"soak_{timestamp}.json")

        try:
            os.makedirs(self.save_dir, exist_ok=True)
            with open(self.json_path, "w") as f:
                json.dump([], f) 
            self.gcode.respond_info(f"Logging data to: soak_{timestamp}.json")
        except Exception as e:
            self.gcode.respond_info(f"Storage error: {e}")

        self.script_start_time = time.time()
        self.soak_start_time = None
        self.is_heating = True
        self.is_running = True

        self.gcode.respond_info("Step 1: Running initial mesh...")
        self.mesh_start_time = time.time()
        self.gcode.run_script_from_command(f"{self.mesh_cmd}\n_SOAK_AFTER_FIRST")

    def cmd_ABORT_SOAK(self, gcmd):
        if not self.is_running:
            self.gcode.respond_info("No SOAK process is currently running.")
            return
        
        # Abort immediato della logica
        self.is_running = False
        self.is_heating = False
        self.gcode.respond_info("!!! SOAK ABORTED BY USER !!!")
        
        # Spegne il piatto in modo sicuro
        self.gcode.run_script_from_command(f"SET_HEATER_TEMPERATURE HEATER={self.heater} TARGET=0")

    def cmd__SOAK_AFTER_FIRST(self, gcmd):
        if not self.is_running: return
        self.gcode.respond_info(f"Step 2: Heating {self.heater} to {self.temp}C...")
        self.gcode.run_script_from_command(f"SET_HEATER_TEMPERATURE HEATER={self.heater} TARGET={self.temp}\n_SOAK_LOOP_EVAL")

    def cmd__SOAK_LOOP_EVAL(self, gcmd):
        if not self.is_running: return
        try:
            sensor_obj = self.printer.lookup_object(self.sensor_name)
            status = sensor_obj.get_status(self.printer.get_reactor().monotonic())
            current_temp = status.get('temperature', 0.0)
        except: return

        if self.is_heating:
            if current_temp >= self.temp:
                self.is_heating = False
                self.soak_start_time = time.time()
                self.gcode.respond_info(f"Target reached! Soaking for {self.duration_sec/60.0} min.")
        else:
            elapsed = time.time() - self.soak_start_time
            if elapsed >= self.duration_sec:
                self.is_running = False
                self.gcode.respond_info("SOAK COMPLETE! Starting Animation...")
                self.run_plotter()
                self.gcode.run_script_from_command(f"SET_HEATER_TEMPERATURE HEATER={self.heater} TARGET=0")
                return 
            self.gcode.respond_info(f"Soaking... {int(self.duration_sec - elapsed)}s left.")

        self.mesh_start_time = time.time()
        self.gcode.run_script_from_command(f"{self.mesh_cmd}\n_SOAK_LOOP_WAIT")

    def run_plotter(self):
        try:
            subprocess.Popen([self.klipper_python, self.plot_script_path, self.json_path])
        except Exception as e:
            self.gcode.respond_info(f"Plotter failed: {e}")

    def cmd__SOAK_LOOP_WAIT(self, gcmd):
        if not self.is_running: return
        
        reactor = self.printer.get_reactor()
        eventtime = reactor.monotonic()
        
        try:
            bed_mesh = self.printer.lookup_object('bed_mesh', None)
            sensor_obj = self.printer.lookup_object(self.sensor_name)
            current_temp = sensor_obj.get_status(eventtime).get('temperature', 0.0)

            if bed_mesh is not None:
                mesh_status = bed_mesh.get_status(eventtime)
                matrix = mesh_status.get('probed_matrix') or mesh_status.get('mesh_matrix', [[]])
                
                mesh_min = mesh_status.get('mesh_min', [0.0, 0.0])
                mesh_max = mesh_status.get('mesh_max', [300.0, 300.0])

                with open(self.json_path, "r") as f: data = json.load(f)
                data.append({
                    "time": time.time() - self.script_start_time, 
                    "temp": current_temp, 
                    "matrix": matrix,
                    "mesh_min": mesh_min,
                    "mesh_max": mesh_max
                })
                with open(self.json_path, "w") as f: json.dump(data, f)
        except: pass

        # Calcolo dell'attesa senza usare G4 (non blocca la console)
        mesh_time = time.time() - self.mesh_start_time
        wait_time = max(1.0, (math.ceil((mesh_time + 3.0) / 5.0) * 5.0) - mesh_time)
        
        # Registra un timer asincrono in Klipper
        reactor.register_timer(self._trigger_next_eval, eventtime + wait_time)

    def _trigger_next_eval(self, eventtime):
        if self.is_running:
            self.gcode.run_script_from_command("_SOAK_LOOP_EVAL")
        return self.printer.get_reactor().NEVER

def load_config(config):
    return SoakMyBed(config)
