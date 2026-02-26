import time
import tkinter as tk
from tkinter import ttk
from tkinter import scrolledtext

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
from matplotlib.widgets import CheckButtons

class MatPlotCheckButton:
    """Wrapper um Matplotlib CheckButtons."""
    def __init__(self, ax, labels, actives, line_colors, callback):
        # Wir nutzen die übergebene Axis (linke Spalte) komplett
        self.widget = CheckButtons(ax, labels, actives)
        self.line_colors = line_colors
        self.widget.on_clicked(callback)
        self._apply_style()

    def _apply_style(self):
        for i, label_obj in enumerate(self.widget.labels):
            label_text = label_obj.get_text()
            label_obj.set_fontsize(9)
            
            col = self.line_colors.get(label_text, 'black')
            
            # Box
            if i < len(self.widget.rectangles):
                rect = self.widget.rectangles[i]
                rect.set_facecolor('white')
                rect.set_edgecolor(col)
                rect.set_linewidth(1.5)
            
            # Haken
            if i < len(self.widget.lines):
                xls = self.widget.lines[i]
                if isinstance(xls, (list, tuple)):
                    for l in xls:
                        l.set_color(col)
                        l.set_linewidth(2.0)
                else:
                    xls.set_color(col)

class ModulePlot:
    def __init__(self, ax_plot, ax_controls_left, ax_controls_right, module, all_modules):
        self.ax = ax_plot
        self.ax2 = ax_plot.twinx()
        self.ax_controls_left = ax_controls_left
        self.ax_controls_right = ax_controls_right
        
        self.module = module
        self.all_modules = all_modules
        
        self.lines = {}
        self.history_keys = []
        self.check_wrapper_left = None
        self.check_wrapper_right = None
        
        self._setup()
        
    def _setup(self):
        from itertools import cycle
        self.ax.set_title(self.module.name, loc='left', fontsize=10, pad=2)
        metrics = self.module.get_metrics()
        
        plots = self.module.plot_config
        y2plots = getattr(self.module, 'y2plot_config', [])
        
        # Listen für Links (Y1) und Rechts (Y2)
        cb_data_left = {'labels': [], 'actives': []}
        cb_data_right = {'labels': [], 'actives': []}

        # Farb-Paletten trennen: 
        # Y1 (Links): Kühle Farben (Blau, Grün, Lila, Türkis, Grau)
        # Y2 (Rechts): Warme Farben (Rot, Orange, Braun, Pink, Oliv)
        colors_y1 = cycle(['#1f77b4', '#2ca02c', '#9467bd', '#17becf', '#7f7f7f'])
        colors_y2 = cycle(['#d62728', '#ff7f0e', '#8c564b', '#e377c2', '#bcbd22'])

        def process_item(item, use_ax2):
            is_visible = not item.startswith('*')
            clean_item = item.lstrip('*')
            target_ax = self.ax2 if use_ax2 else self.ax
            target_colors = colors_y2 if use_ax2 else colors_y1
            
            # Ziel-Listen für Checkboxen
            cb_data = cb_data_right if use_ax2 else cb_data_left
            
            # Helper zum Erstellen der Line
            def add_line(key, label, style_kwargs=None):
                kwargs = style_kwargs or {}
                # Farbe setzen, falls nicht explizit angegeben
                if 'color' not in kwargs:
                    kwargs['color'] = next(target_colors)
                
                line, = target_ax.plot([], [], label=label, visible=is_visible, **kwargs)
                self.lines[key] = line
                self.history_keys.append(key)

            # 1. Lokal
            if clean_item in metrics:
                h_key = f"{self.module.name}.{clean_item}"
                add_line(h_key, clean_item)
                cb_data['labels'].append(clean_item)
                cb_data['actives'].append(is_visible)

            # 2. Cross-Ref / Special
            elif '.' in clean_item:
                t_mod, v_name = clean_item.split('.', 1)
                
                # Special: .cells Wildcard
                if v_name == 'cells' and t_mod in self.all_modules:
                    target_mod = self.all_modules[t_mod]
                    if hasattr(target_mod, 'num_cells'):
                        cb_data['labels'].append(clean_item)
                        cb_data['actives'].append(is_visible)
                        for j in range(target_mod.num_cells):
                            h_key = f"{t_mod}.cell_{j+1}"
                            # Nur erste Linie bekommt Label für Legende
                            lbl = clean_item if j == 0 else None
                            add_line(h_key, lbl, {'linewidth':0.5, 'alpha':0.5})

                elif t_mod in self.all_modules:
                    h_key = f"{t_mod}.{v_name}"
                    add_line(h_key, clean_item)
                    cb_data['labels'].append(clean_item)
                    cb_data['actives'].append(is_visible)

            # 3. Lokal 'cells'
            elif clean_item == 'cells' and hasattr(self.module, 'num_cells'):
                cb_data['labels'].append('cells')
                cb_data['actives'].append(is_visible)
                for j in range(self.module.num_cells):
                    h_key = f"{self.module.name}.cell_{j+1}"
                    lbl = 'cells' if j == 0 else None
                    add_line(h_key, lbl, {'linewidth':0.5, 'alpha':0.5})

        for p in plots: process_item(p, False)
        for p in y2plots: process_item(p, True)

        # Callback Factory
        def create_callback():
            def callback(label):
                if label == 'cells': 
                    self._toggle_group(f"{self.module.name}.cell_")
                elif label.endswith('.cells'):
                    self._toggle_group(label.replace('.cells', '.cell_'))
                else:
                    h_key = label if '.' in label else f"{self.module.name}.{label}"
                    if h_key in self.lines:
                        self.lines[h_key].set_visible(not self.lines[h_key].get_visible())
                
                self.update_legend()
                self.rescale()
                self.ax.figure.canvas.draw_idle()
            return callback

        # Checkboxen Links erstellen
        if cb_data_left['labels']:
            self.ax_controls_left.axis('off')
            line_colors = {l.get_label(): l.get_color() for l in self.lines.values() 
                           if l.get_label() and not l.get_label().startswith('_')}
            self.check_wrapper_left = MatPlotCheckButton(
                self.ax_controls_left, 
                cb_data_left['labels'], 
                cb_data_left['actives'], 
                line_colors, 
                create_callback()
            )
        else:
            self.ax_controls_left.axis('off')

        # Checkboxen Rechts erstellen
        if cb_data_right['labels']:
            self.ax_controls_right.axis('off')
            line_colors = {l.get_label(): l.get_color() for l in self.lines.values() 
                           if l.get_label() and not l.get_label().startswith('_')}
            self.check_wrapper_right = MatPlotCheckButton(
                self.ax_controls_right, 
                cb_data_right['labels'], 
                cb_data_right['actives'], 
                line_colors, 
                create_callback()
            )
        else:
            self.ax_controls_right.axis('off')

    def _toggle_group(self, prefix):
        state = True
        for k, l in self.lines.items():
            if k.startswith(prefix):
                state = not l.get_visible()
                break
        for k, l in self.lines.items():
            if k.startswith(prefix): l.set_visible(state)

    def update_data(self, t_axis, global_history):
        for key in self.history_keys:
            if key in global_history:
                self.lines[key].set_data(t_axis, global_history[key])

    def update_legend(self):
        h, l = [], []
        for ax in [self.ax, self.ax2]:
            for line in ax.get_lines():
                if line.get_visible() and line.get_label() and not line.get_label().startswith('_'):
                    h.append(line)
                    l.append(line.get_label())
        
        if h: self.ax.legend(h, l, loc='upper left', fontsize='x-small', framealpha=0.6)
        elif self.ax.get_legend(): self.ax.get_legend().set_visible(False)

    def rescale(self, t_axis_range=None):
        import numpy as np
        if t_axis_range:
            self.ax.set_xlim(t_axis_range)

        for i, ax in enumerate([self.ax, self.ax2]):
            ymin, ymax = float('inf'), float('-inf')
            found = False
            
            for line in ax.get_lines():
                if line.get_visible():
                    y = line.get_ydata()
                    if len(y) > 0:
                        # Verwende numpy für Geschwindigkeit und Robustheit gegen NaNs
                        y_min = np.nanmin(y)
                        y_max = np.nanmax(y)
                        if y_min < ymin: ymin = y_min
                        if y_max > ymax: ymax = y_max
                        found = True
            
            if found and not (np.isinf(ymin) or np.isinf(ymax)):
                if ymin == ymax:
                    margin = abs(ymin) * 0.1 if ymin != 0 else 1.0
                    ymin -= margin
                    ymax += margin
                else:
                    span = ymax - ymin
                    ymin -= span * 0.05
                    ymax += span * 0.05
                
                ax.set_ylim(ymin, ymax)
                ax.get_yaxis().set_visible(True)
            else:
                # Wenn nichts sichtbar ist oder nur Infs da sind
                if i > 0: # Sekundärachse verstecken
                    ax.get_yaxis().set_visible(False)
                else:
                    # Hauptachse: Default Bereich lassen oder leicht anpassen
                    pass


class SimulationGui:
    def __init__(self, title, modules, sim_params=None):
        self.title = title
        self.modules_list = modules 
        self.modules_map = {m.name: m for m in modules}
        self.sim_params = sim_params or {}
        self.t_axis = []
        self.global_history = {}
        self.module_plots = []
        self.is_fullscreen = False
        
        self.root = tk.Tk()
        self.root.wm_title(self.title)
        self.root.geometry("1300x900")
        
        self.root.bind('q', lambda e: self.root.destroy())
        self.root.bind('f', self.toggle_fullscreen)
        self.root.bind('<Escape>', self.exit_fullscreen)
        # Umfassende Toolbar Keybindings
        self.root.bind('h', lambda e: self.toolbar.home())
        self.root.bind('b', lambda e: self.toolbar.back())
        self.root.bind('v', lambda e: self.toolbar.forward())
        self.root.bind('p', lambda e: self.toolbar.pan())
        self.root.bind('z', lambda e: self.toolbar.zoom())
        self.root.bind('s', lambda e: self.toolbar.save_figure())
        self.root.bind('c', lambda e: self.toolbar.configure_subplots())

        # Main Layout
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=1)

        self.canvas_container = tk.Canvas(main_frame)
        self.scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=self.canvas_container.yview)
        
        self.scrollable_frame = ttk.Frame(self.canvas_container)
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas_container.configure(scrollregion=self.canvas_container.bbox("all"))
        )

        self.window_id = self.canvas_container.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas_container.configure(yscrollcommand=self.scrollbar.set)
        self.canvas_container.bind('<Configure>', self._on_canvas_resize)
        
        # Mausrad-Bindung
        self.canvas_container.bind_all('<MouseWheel>', self._on_mouse_wheel) # Windows/macOS
        self.canvas_container.bind_all('<Button-4>', self._on_mouse_wheel)   # Linux Scroll Up
        self.canvas_container.bind_all('<Button-5>', self._on_mouse_wheel)   # Linux Scroll Down

        self.canvas_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=1)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Matplotlib Figure: N Zeilen, 3 Spalten (Controls Left, Plot, Controls Right)
        total_height = max(8, len(modules) * 3.0)
        self.fig = Figure(figsize=(12, total_height), dpi=100)
        
        # Gridspec: Links 12%, Mitte 76%, Rechts 12%
        # sharex='col' -> Rechte Spalte (Index 1) teilt sich X-Achse
        self.axs_grid = self.fig.subplots(
            len(modules), 3, 
            sharex='col', 
            gridspec_kw={'width_ratios': [0.12, 0.76, 0.12], 'wspace': 0.05, 'hspace': 0.3}
        )
        
        # Sicherstellen, dass axs_grid immer 2D Array ist [[ax_cl, ax_p, ax_cr], ...]
        if len(modules) == 1:
            self.axs_grid = [self.axs_grid] # Wrap in list
        
        self.fig.subplots_adjust(left=0.05, top=0.96, bottom=0.05, right=0.95)
        self.fig.suptitle(self.title, fontsize=14, fontweight='bold')
        self._show_params()
        
        # X-Label an unterstem Plot der mittleren Spalte (Index 1)
        self.axs_grid[-1][1].set_xlabel('Zeit [h]')
        
        self._init_module_plots()

        self.canvas_mpl = FigureCanvasTkAgg(self.fig, master=self.scrollable_frame)
        self.canvas_mpl.draw()
        self.canvas_mpl.get_tk_widget().pack(fill=tk.BOTH, expand=1)
        
        # Log-Bereich ganz unten (feststehend, kompakt)
        self.log_frame = tk.Frame(self.root)
        self.log_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.log_widget = scrolledtext.ScrolledText(
            self.log_frame, 
            height=4, 
            font=("Consolas", 8), 
            state='disabled', 
            bg="#f0f0f0", 
            fg="#333333",
            padx=2,
            pady=2,
            borderwidth=1,
            relief="sunken"
        )
        self.log_widget.vbar.configure(width=10)
        self.log_widget.pack(fill=tk.BOTH, expand=1, padx=0, pady=0)
        
        # Tags für Farben definieren
        self.log_widget.tag_config('Info', foreground='black')
        self.log_widget.tag_config('Warning', foreground='blue')
        self.log_widget.tag_config('Error', foreground='red')

        self.toolbar = NavigationToolbar2Tk(self.canvas_mpl, self.root)
        self.toolbar.update()
        self.toolbar.pack(side=tk.BOTTOM, fill=tk.X)
       
        self.lastUpdate = time.time()

    def log(self, message, level='Info'):
        """Fügt eine Nachricht zum Log-Widget hinzu. Level steuert die Farbe."""
        self.log_widget.configure(state='normal')
        timestamp = time.strftime("%H:%M:%S")
        
        # Zeitstempel normal, Nachricht farbig
        self.log_widget.insert(tk.END, f"[{timestamp}] ")
        self.log_widget.insert(tk.END, f"{message}\n", level)
        
        self.log_widget.see(tk.END)
        self.log_widget.configure(state='disabled')
        self.root.update_idletasks()

    def _on_canvas_resize(self, event):
        self.canvas_container.itemconfig(self.window_id, width=event.width)

    def _on_mouse_wheel(self, event):
        if event.num == 4 or event.delta > 0:
            self.canvas_container.yview_scroll(-1, "units")
        elif event.num == 5 or event.delta < 0:
            self.canvas_container.yview_scroll(1, "units")

    def _show_params(self):
        if self.sim_params:
            p = self.sim_params
            param_str = f"n_steps: {p.get('n_steps')} | time_step: {p.get('time_step')}s | t_sim: {p.get('t_simulation')}s"
            self.fig.text(0.5, 0.985, param_str, ha='center', fontsize=9, color='gray')

    def _init_module_plots(self):
        for i, mod in enumerate(self.modules_list):
            row = self.axs_grid[i]
            ax_ctl_left = row[0]
            ax_plt = row[1]
            ax_ctl_right = row[2]
            
            mp = ModulePlot(ax_plt, ax_ctl_left, ax_ctl_right, mod, self.modules_map)
            self.module_plots.append(mp)
            
            ax_plt.grid(True, linestyle='--', alpha=0.6)
            mp.update_legend()

    def toggle_fullscreen(self, event=None):
        self.is_fullscreen = not self.is_fullscreen
        self.root.attributes("-fullscreen", self.is_fullscreen)

    def exit_fullscreen(self, event=None):
        if self.is_fullscreen:
            self.is_fullscreen = False
            self.root.attributes("-fullscreen", False)

    def update(self, t_hours, all_metrics):
        self.t_axis.append(t_hours)
        t_range = (min(self.t_axis), max(self.t_axis)) if self.t_axis else (0, 1)

        for mod_name, metrics in all_metrics.items():
            for var, val in metrics.items():
                key = f"{mod_name}.{var}"
                if key not in self.global_history: self.global_history[key] = []
                self.global_history[key].append(val)

        for mp in self.module_plots:
            mp.update_data(self.t_axis, self.global_history)

        if time.time() - self.lastUpdate > 0.3:
            for mp in self.module_plots:
                mp.rescale(t_range)
            self.canvas_mpl.draw_idle()
            self.root.update()
            self.lastUpdate = time.time()

    def start_simulation_loop(self, step_callback, delay_ms=1):
        def _loop():
            keep_running = step_callback()
            if keep_running:
                self.root.after(delay_ms, _loop)
            else:
                print("Simulation beendet.")
        self.root.after(delay_ms, _loop)

    def show(self):
        print("GUI bereit. Fenster schließen zum Beenden.")
        self.root.mainloop()