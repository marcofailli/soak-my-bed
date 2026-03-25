import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from scipy.interpolate import griddata
import matplotlib.gridspec as gridspec
import json
import argparse
import os

def generate_soak_plot(json_path):
    if not os.path.exists(json_path):
        print(f"Error: File {json_path} not found.")
        return

    with open(json_path, 'r') as f:
        data = json.load(f)

    if not data:
        print("Error: No data found in JSON.")
        return

    # Estrazione dati
    times_raw = [d['time'] for d in data]
    temps = [d['temp'] for d in data]
    z_frames = [np.array(d['matrix']) for d in data]
    
    rows, cols = z_frames[0].shape
    plate_x, plate_y = 405, 410 # Dimensioni Voron standard
    points_x = np.linspace(0, plate_x, cols)
    points_y = np.linspace(0, plate_y, rows)
    X, Y = np.meshgrid(points_x, points_y)
    grid_x, grid_y = np.mgrid[0:plate_x:100j, 0:plate_y:100j]

    # Calcolo metriche di stabilità
    avg_var_vs_first = []
    avg_var_vs_prev = []
    first_mesh = z_frames[0]
    
    for i in range(len(z_frames)):
        curr = z_frames[i]
        avg_var_vs_first.append(np.mean(np.abs(curr - first_mesh)))
        if i == 0:
            avg_var_vs_prev.append(0)
        else:
            avg_var_vs_prev.append(np.mean(np.abs(curr - z_frames[i-1])))

    # Setup Grafico
    plt.style.use('bmh')
    fig = plt.figure(figsize=(12, 10), facecolor='#f8f8f8')
    gs = gridspec.GridSpec(2, 1, height_ratios=[3, 1])
    
    ax3d = fig.add_subplot(gs[0], projection='3d')
    ax2d = fig.add_subplot(gs[1])
    
    # Creazione del secondo asse Y per la temperatura
    ax_temp = ax2d.twinx() 

    z_min_abs = np.min(z_frames)
    z_max_abs = np.max(z_frames)
    z_scale = 60 

    def update(frame):
        ax3d.clear()
        ax2d.clear()
        ax_temp.clear()
        
        curr_z = z_frames[frame]
        z_interp = griddata((X.flatten(), Y.flatten()), curr_z.flatten(), 
                            (grid_x, grid_y), method='cubic')
        
        # --- 3D SURFACE ---
        surf = ax3d.plot_surface(grid_x, grid_y, z_interp * z_scale, cmap='turbo',
                                 vmin=z_min_abs * z_scale, vmax=z_max_abs * z_scale,
                                 edgecolor='k', linewidth=0.1, alpha=0.8)
        
        m, s = divmod(int(times_raw[frame]), 60)
        stats = (f"Time: {m:02d}:{s:02d} | Temp: {temps[frame]:.1f}C\n"
                 f"Deformation: {avg_var_vs_first[frame]:.4f}mm")
        ax3d.text2D(0.02, 0.95, stats, transform=ax3d.transAxes, family='monospace', bbox=dict(facecolor='white', alpha=0.7))
        
        ax3d.set_zlim(z_min_abs*z_scale*2, z_max_abs*z_scale*2)
        ax3d.view_init(elev=25, azim=-45)

        # --- 2D STABILITY & TEMPERATURE ---
        time_mins = [t / 60.0 for t in times_raw[:frame+1]]
        
        # Plot Variazioni (Asse Y sinistro)
        p1, = ax2d.plot(time_mins, avg_var_vs_first[:frame+1], color='#1f77b4', label='Total Shift (mm)', linewidth=2)
        p2, = ax2d.plot(time_mins, avg_var_vs_prev[:frame+1], color='#d62728', linestyle='--', label='Instant Stability (mm)')
        
        # Plot Temperatura (Asse Y destro)
        p3, = ax_temp.plot(time_mins, temps[:frame+1], color='#ff7f0e', label='Bed Temp (°C)', linewidth=1.5, alpha=0.8)
        
        ax2d.set_xlim(0, max(5, max(times_raw) / 60.0))
        ax2d.set_ylim(0, max(0.1, max(avg_var_vs_first) * 1.2))
        ax_temp.set_ylim(min(temps)-5, max(temps)+5)
        
        ax2d.set_xlabel("Time (Minutes)")
        ax2d.set_ylabel("Variation (mm)")
        ax_temp.set_ylabel("Temperature (°C)")
        
        # Unione delle legende
        lines = [p1, p2, p3]
        ax2d.legend(lines, [l.get_label() for l in lines], loc='upper left', fontsize='small')
        
        return surf,

    ani = FuncAnimation(fig, update, frames=len(z_frames), interval=200)
    output_gif = json_path.replace('.json', '.gif')
    ani.save(output_gif, writer='pillow', fps=8)
    print(f"Animation saved: {output_gif}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    args = parser.parse_args()
    generate_soak_plot(args.input)
