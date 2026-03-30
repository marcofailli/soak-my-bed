<p align="center">
  <img src="https://raw.githubusercontent.com/marcofailli/Soak-My-Bed/main/banner.png?v=2" width="100%" alt="Soak My Bed Banner">
</p>

---

<h1 align="center"><strong>SOAK MY BED</strong></h1>

<p align="center">
  <strong>The definitive Klipper tool for thermal stability analysis.</strong>
</p>

---

### 📘 What is Soak My Bed?
All 3D printer beds and frames undergo significant physical deformation as they heat up, a phenomenon known as thermal drift. **Soak My Bed** is a Klipper plugin that eliminates the "guessing game" of heat soaking. Instead of waiting for a random timer, this tool measures the actual physical movement of your hardware in real-time, allowing you to consciously know how long you should wait before starting a print and how the printer heating-up affects its geometry.

### ✨ Key Features
* **Full Automation:** Handles Bed Meshing in a continuous loop for as long as you wish.
* **Smart Time Logic:** Automatically calculates the optimal interval between meshes, adding a safety buffer and rounding to the nearest 5-second mark for consistent data points.
* **Auto-Scaling & Bed Detection:** Automatically reads your mesh boundaries directly from Klipper. It works out-of-the-box on any printer size (Voron, Prusa, Ender, etc.) without manual configuration.
* **History Tracking:** Saves uniquely timestamped JSON and GIF files (e.g., `0260330_0938_110C_45m.gif`) in your `soak_data` folder so you never overwrite or lose your previous test data.
* **Dual Stability Tracking:** Monitors variations relative to the initial "cold" state and the immediate "previous" mesh to identify equilibrium.
* **Visual Analytics:** Generates a 3D animation (GIF) and stability curves to visualize the evolution of the deformation of your printer.
* **Instant Abort:** Stop the process at any time with `ABORT_SOAK`. The script uses non-blocking logic to instantly halt the heater and still generate a complete graph of the data collected so far.

### ⚙️ How it works
The plugin operates by running successive `BED_MESH_CALIBRATE` cycles. After each mesh, the script captures the Z-matrix and the current bed temperature. It then calculates the **Mean Absolute Error (MAE)**:
1. **Variation vs First Mesh:** Tells you the total amount of deformation your bed has undergone since the beginning of the soak.
2. **Variation vs Previous Mesh:** As this value approaches zero and the graph flattens into a horizontal line, it indicates that the thermal expansion has ceased. At this point, the frame and bed are in equilibrium, and your Z-offset will remain stable throughout the print.

### 🖼️ Thermal Evolution Plot
<p align="center">
  <img src="test_plot.gif" width="100%" alt="Thermal Stability Animation">
</p>

> **How to read this graph:** > The top 3D plot shows the physical warping of the bed (exaggerated for clarity). In the bottom 2D plot, focus on the **Red Dashed Line** (Vs Prev Mesh). When this line stays flat and close to zero, your printer has stopped moving. The **Blue Line** shows how much your bed has moved in total from its original position—this explains why a first layer might fail if you don't wait for the soak to complete!

---

### 🚀 Installation

1. **Clone the repository** to your Klipper host (Raspberry Pi/BTT Pi):
    ```bash
    cd ~
    git clone https://github.com/marcofailli/soak-my-bed.git
    ```
2. **Run the automated installer**:
   *(This step might take a while since we are installing system dependencies and Python plotting libraries like SciPy. Be patient!)*
    ```bash
    cd soak-my-bed
    chmod +x install.sh
    ./install.sh
    ```
3. **Configure Klipper**: Add the following line anywhere in your `printer.cfg`:
    ```ini
    [soak_my_bed]
    ```
4. **Enable Automatic Updates**: Add the following in your `moonraker.conf`:
    ```ini
    [update_manager soak-my-bed]
    type: git_repo
    path: ~/soak-my-bed
    origin: https://github.com/marcofailli/soak-my-bed.git
    primary_branch: main
    install_script: install.sh
    managed_services: klipper
    ```
5. **Restart Klipper**:
    ```bash
    sudo systemctl restart klipper
    ```

---

### 🗂️ Custom Path Configuration (Creality OS, Sovol, BTT, etc.)

By default, **SoakMyBed** automatically detects your current user's home directory (whether it's `pi`, `sovol`, `biqu`, or `elegoo`) and finds the correct Python environment dynamically. You don't need to change anything for standard setups!

However, if your Klipper installation is completely custom or runs on a locked-down system like **Creality K1/K1C**, you can manually override the default paths directly in your `printer.cfg`. Just add these variables under the main section:

```ini
[soak_my_bed]
save_dir: /usr/data/printer_data/config/soak_data
plot_script_path: /usr/data/soak-my-bed/scripts/plotter.py
# Optional: customize your mesh command (defaults to BED_MESH_CALIBRATE)
mesh_command: BED_MESH_CALIBRATE METHOD=rapid_scan
```

---

### 🛠️ Usage

Before running the script you will have to execute your usual homing routine (that might include `G28`, `QUAD_GANTRY_LEVEL`, ...).

It is recommended to start the script with your printer cold, in equilibrium with ambient temperature, to actually evaluate its behavior when starting a fresh new print. 
Heat soaking is a slow process that continues well after reaching your bed target temperature; a typical soak cycle lasts about 60 minutes... **Don't rush!**

While meshing, KlipperScreen will probably prompt you to save the new `config`, just discard this message.

#### Commands
* `SOAK_MY_BED TEMPERATURE=100 DURATION=60`
    * Sets the bed to 100°C. It will wait until the target temperature is reached, then run the analysis for exactly 60 minutes.
* `SOAK_MY_BED`
    * Runs with default values (Target: 60°C, Duration: 10 minutes).
* `SOAK_MY_BED TEMPERATURE=110 DURATION=45 HEATER=heater_bed MESH_COMMAND="BED_MESH_CALIBRATE METHOD=rapid_scan"`
    * **Advanced:** You can override the default heater name and the specific mesh command you want to use (e.g., if you want to use a specific macro or beacon scan method).
* `ABORT_SOAK`
    * Stops the process immediately, turns off the heater, and triggers the generation of the GIF with the data collected up to that moment.

*Note: Once the process is completed or aborted, you can find your animated GIF (and the image of its final frame) inside the `printer_data/config/soak_data` folder directly from the Mainsail/Fluidd web interface!*

---
<p align="center">
  Released under the MIT License. Created by <b>marcofailli</b>.
</p>
