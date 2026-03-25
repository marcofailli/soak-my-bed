import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from scipy.interpolate import griddata
import matplotlib.gridspec as gridspec
import json
import argparse
import os

def generate_soak_plot(json_path):
    # 1. Load Data from JSON
    if not os.path.exists(json_path):
        print(f"Error: File {json_path} not found.")
        return

    with open(json_path, 'r') as f:
        data = json.load(f)

    if not data:
        print("Error: No data found in JSON.")
        return

    # Extracting structures from JSON
    # Expected JSON format: list of dicts {'time': sec, 'temp': t, 'matrix': [[...]]}
    times_raw = [d['time'] for d in data]
    temps = [d['temp'] for d in data]
    z_frames = [np.array(d['matrix']) for d in data]
    
    # Calculate intervals (for HUD display)
    if len(times_raw) > 1:
        interval_sec = times_raw[1] - times_raw[0]
    else:
        interval_sec = 0

    # 2. Setup Bed Geometry
    # Assuming standard Voron 405x410, but we derive grid from matrix shape
    rows, cols = z_frames[0].shape
    plate_x, plate_y = 405, 410 # Default dimensions
    points_x = np.linspace(0, plate_x, cols)
    points_y = np.linspace(0, plate_y, rows)
    X, Y = np.meshgrid(points_x, points_y)
    
    # High-resolution grid for smooth interpolation (100x100)
    grid_x, grid_y = np.mgrid[0:plate_x:100j, 0:plate_y:100j]

    # 3. Calculate Thermal Stability Metrics
    avg_var_vs_first = []
    avg_var_vs_prev = []
    first_mesh = z_frames[0]
    
    for i in range(len(z_frames)):
        curr = z_frames[i]
        # Mean Absolute Error (MAE) relative to the cold/first mesh
        avg_var_vs_first.append(np.mean(np.abs(curr - first_mesh)))
        # MAE relative to the previous mesh (checks for equilibrium)
        if i == 0:
            avg_var_vs_prev.append(0)
        else:
            avg_var_vs_prev.append(np.mean(np.abs(curr - z_frames[i-1])))

    # 4. Visualization Setup
    plt.style.use('bmh')
    fig = plt.figure(figsize=(12, 10), facecolor='#f8f8f8')
    gs = gridspec.GridSpec(2, 1, height_ratios=[3, 1])
    
    ax3d = fig.add_subplot(gs[0], projection='3d')
    ax2d = fig.add_subplot(gs[1])
    
    # Global Z limits to keep the scale consistent across frames
    z_min_abs = np.min(z_frames)
    z_max_abs = np.max(z_frames)
    z_scale = 60  # Visual exaggeration factor for small thermal shifts

    def update(frame):
        ax3d.clear()
        ax2d.clear()
        
        curr_z = z_frames[frame]
        # Cubic interpolation for a smooth "liquid" surface look
        z_interp = griddata((X.flatten(), Y.flatten()), curr_z.flatten(), 
                            (grid_x, grid_y), method='cubic')
        
        # --- TOP PLOT: 3D SURFACE ---
        surf = ax3d.plot_surface(grid_x, grid_y, z_interp * z_scale, cmap='turbo',
                                 vmin=z_min_abs * z_scale, vmax=z_max_abs * z_scale,
                                 edgecolor='k', linewidth=0.1, alpha=0.8, antialiased=True)
        
        # Reference Zero Plane (Semi-transparent gray)
        ax3d.plot_surface(grid_x, grid_y, grid_x*0, color='gray', alpha=0.1) 
        
        # HUD (Heads-Up Display)
        m, s = divmod(int(times_raw[frame]), 60)
        stats = (f"SOAK MY BED - Frame {frame+1}/{len(z_frames)}\n"
                 f"Time Elapsed: {m:02d}:{s:02d}\n"
                 f"Bed Temp:     {temps[frame]:.1f} C\n"
                 f"Avg Var (vs First): {avg_var_vs_first[frame]:.4f} mm\n"
                 f"Avg Var (vs Prev):  {avg_var_vs_prev[frame]:.4f} mm")
        
        ax3d.text2D(0.02, 0.95, stats, transform=ax3d.transAxes, family='monospace', 
                    fontsize=10, bbox=dict(facecolor='white', alpha=0.8, boxstyle='round'))
        
        ax3d.set_zlim(z_min_abs*z_scale*2, z_max_abs*z_scale*2)
        ax3d.view_init(elev=25, azim=-45)
        ax3d.set_title("3D Thermal Deformation", pad=10)

        # --- BOTTOM PLOT: STABILITY CURVES ---
        # X-axis in minutes
        time_mins = [t / 60.0 for t in times_raw[:frame+1]]
        ax2d.plot(time_mins, avg_var_vs_first[:frame+1], color='#1f77b4', label='Total Shift (vs First)', linewidth=2)
        ax2d.plot(time_mins, avg_var_vs_prev[:frame+1], color='#d62728', linestyle='--', label='Instant Stability (vs Prev)', alpha=0.7)
        
        # Formatting 2D Plot
        ax2d.set_xlim(0, max(5, max(times_raw) / 60.0))
        ax2d.set_ylim(0, max(0.05, max(avg_var_vs_first) * 1.2))
        ax2d.set_xlabel("Time (Minutes)")
        ax2d.set_ylabel("Mean Variation (mm)")
        ax2d.legend(loc='upper left', fontsize='small')
        ax2d.grid(True, alpha=0.3)
        
        return surf,

    # 5. Animation Generation
    ani = FuncAnimation(fig, update, frames=len(z_frames), interval=200)
    
    output_gif = json_path.replace('.json', '.gif')
    print(f"Rendering animation to: {output_gif}...")
    
    # Save using 'pillow' writer (standard on most Linux distros)
    ani.save(output_gif, writer='pillow', fps=8)
    print("Done!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Heat Soak Animation from Klipper JSON data.")
    parser.add_argument("input", help="Path to the soak_my_bed_data.json file")
    args = parser.parse_args()
    
    generate_soak_plot(args.input)
