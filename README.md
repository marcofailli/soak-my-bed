<p align="center">
  <img src="https://raw.githubusercontent.com/marcofailli/Soak-My-Bed/main/banner.png" width="100%" alt="Soak My Bed Banner">
</p>

---

<h1 align="center"><strong>SOAK MY BED</strong></h1>

<p align="center">
  <strong>The definitive Klipper tool for thermal stability analysis and automated heat soaking.</strong>
</p>

---

### 📘 What is Soak My Bed?
Most 3D printer beds and frames undergo significant physical deformation as they heat up, a phenomenon known as thermal drift. **Soak My Bed** is a Klipper plugin that eliminates the "guessing game" of heat soaking. Instead of waiting for a random timer, this tool measures the actual physical movement of your hardware in real-time, allowing you to start printing exactly when your machine has reached a true steady state.

### ✨ Key Features
* **Full Automation:** Handles Homing, Quad Gantry Leveling, and Bed Meshing in a continuous loop.
* **Smart Time Logic:** Automatically calculates the optimal interval between meshes, adding a safety buffer and rounding to the nearest 5-second mark for consistent data points.
* **Dual Stability Tracking:** Monitors variations relative to the initial "cold" state and the immediate "previous" mesh to identify equilibrium.
* **Visual Analytics:** Generates a high-resolution 3D animation (GIF) and stability curves to visualize the "breathing" of your printer.
* **Interruptible Workflow:** Stop the process at any time with `CANCEL_SOAK` and still get a complete graph of the data collected so far.

### ⚙️ How it works in detail
The plugin operates by running successive `BED_MESH_CALIBRATE` cycles. After each mesh, the script captures the Z-matrix and the current bed temperature. It then calculates the **Mean Absolute Error (MAE)**:
1.  **Variation vs First Mesh:** Tells you the total amount of deformation your bed has undergone since the beginning of the soak.
2.  **Variation vs Previous Mesh:** This is the most critical metric. As this value approaches zero and the graph flattens into a horizontal line, it indicates that the thermal expansion has ceased. At this point, the frame and bed are in equilibrium, and your Z-offset will remain stable throughout the print.

### 🖼️ Thermal Evolution Preview
<p align="center">
  <img src="soak_my_bed_data.gif" width="100%" alt="Thermal Stability Animation">
</p>

> **How to read this graph:** > The top 3D plot shows the physical warping of the bed (exaggerated for clarity). In the bottom 2D plot, focus on the **Red Dashed Line** (Vs Prev Mesh). When this line stays flat and close to zero, your printer has stopped moving. The **Blue Line** shows how much your bed has moved in total from its original position—this explains why a first layer might fail if you don't wait for the soak to complete!

---

### 🚀 Installation

1.  **Clone the repository** to your Klipper host (Raspberry Pi/BTT Pi):
    ```bash
    cd ~
    git clone [https://github.com/marcofailli/Soak-My-Bed.git](https://github.com/marcofailli/Soak-My-Bed.git)
    ```
2.  **Run the automated installer**:
    ```bash
    cd Soak-My-Bed
    chmod +x install.sh
    ./install.sh
    ```
3.  **Configure Klipper**: Add the following line anywhere in your `printer.cfg`:
    ```ini
    [soak_my_bed]
    ```
4.  **Restart Klipper**:
    ```bash
    sudo systemctl restart klipper
    ```

---

### 🛠️ Usage

#### Commands
* `SOAK_MY_BED TEMP=100 DURATION=60`
    * Sets the bed to 100°C and runs the analysis for exactly 60 minutes.
* `SOAK_MY_BED TEMP=60`
    * Sets the bed to 60°C. It will run until the target temperature is reached, then continue for an additional **30 minutes** of stabilization.
* `CANCEL_SOAK`
    * Stops the process immediately, turns off the heater, and triggers the generation of the GIF with the data collected up to that moment.

---
<p align="center">
  Released under the MIT License. Created by <b>marcofailli</b>.
</p>
