import os
import subprocess
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import queue

class ImageScalerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Image Scaling Tool")
        self.root.geometry("400x400")  # Set the window size
        self.root.resizable(False, False)  # Make the window fixed size
        self.center_window()

        # Setup style
        self.style = ttk.Style()
        self.style.configure('TLabel', font=('Arial', 12))
        self.style.configure('TEntry', font=('Arial', 12))
        self.style.configure('TButton', font=('Arial', 12))
        self.style.configure('TScale', font=('Arial', 10))

        # Select Folder
        self.create_select_folder_section()

        # Scale Section
        self.create_scale_section()

        # Batch Section
        self.create_batch_section()

        # Progress Bar
        self.create_progress_bar_section()

        # Scale Button
        self.create_scale_button()

        # Variables to track progress
        self.total_images = 0
        self.processed_images = 0
        self.progress_queue = queue.Queue()

    def center_window(self):
        """Center the window on the screen."""
        self.root.update_idletasks()  # Update "requested size" from geometry manager
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def create_select_folder_section(self):
        frame = tk.Frame(self.root)
        frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        
        tk.Label(frame, text="Select Folder:").pack(side=tk.LEFT, padx=5)
        self.folder_entry = tk.Entry(frame, width=30)
        self.folder_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Button(frame, text="Browse", command=self.select_folder).pack(side=tk.LEFT, padx=5)

    def create_scale_section(self):
        frame = tk.Frame(self.root)
        frame.grid(row=1, column=0, padx=10, pady=10, sticky="ew")
        
        tk.Label(frame, text="Scale (%):").pack(side=tk.LEFT, padx=5)
        self.scale_entry = tk.Spinbox(frame, from_=0, to=200, width=5)
        self.scale_entry.pack(side=tk.LEFT, padx=5)
        self.scale_entry.delete(0, tk.END)
        self.scale_entry.insert(0, 100)  # Default to 100%
        
        # Bind Enter key to update scale
        self.scale_entry.bind('<Return>', self.update_scale_from_entry)

        self.scale_slider = tk.Scale(self.root, from_=0, to=200, orient=tk.HORIZONTAL, command=self.update_scale_from_slider)
        self.scale_slider.set(100)  # Default to 100%
        self.scale_slider.grid(row=2, column=0, padx=10, pady=5, sticky="ew")

    def create_batch_section(self):
        frame = tk.Frame(self.root)
        frame.grid(row=3, column=0, padx=10, pady=10, sticky="ew")

        tk.Label(frame, text="Images per Batch:").pack(side=tk.LEFT, padx=5)
        self.batch_entry = tk.Spinbox(frame, from_=1, to=500, width=5)
        self.batch_entry.pack(side=tk.LEFT, padx=5)
        self.batch_entry.delete(0, tk.END)
        self.batch_entry.insert(0, 250)  # Default to 250
        
        # Bind Enter key to update batch
        self.batch_entry.bind('<Return>', self.update_batch_from_entry)

        self.batch_slider = tk.Scale(self.root, from_=1, to=500, orient=tk.HORIZONTAL, command=self.update_batch_from_slider)
        self.batch_slider.set(250)  # Default to 250
        self.batch_slider.grid(row=4, column=0, padx=10, pady=5, sticky="ew")

    def create_progress_bar_section(self):
        tk.Label(self.root, text="Progress:").grid(row=5, column=0, padx=10, pady=10, sticky="w")
        self.progress_bar = ttk.Progressbar(self.root, orient="horizontal", mode="determinate", length=350)
        self.progress_bar.grid(row=6, column=0, padx=10, pady=10)

    def create_scale_button(self):
        tk.Button(self.root, text="Scale Images", command=self.start_scaling_thread).grid(row=7, column=0, padx=10, pady=20, sticky="e")

    def select_folder(self):
        """Open a folder dialog and set the folder path."""
        folder_path = filedialog.askdirectory(title="Select Folder with Images")
        if folder_path:
            self.folder_entry.delete(0, tk.END)
            self.folder_entry.insert(0, folder_path)

    def start_scaling_thread(self):
        """Start the scaling process in a separate thread."""
        threading.Thread(target=self.scale_images).start()
        threading.Thread(target=self.update_progress_from_queue).start()

    def scale_images(self):
        """Get inputs and run the scaling script."""
        folder_path = self.folder_entry.get()
        scale = self.scale_entry.get()
        images_per_batch = self.batch_entry.get()

        if not folder_path or not scale or not images_per_batch:
            messagebox.showwarning("Input Error", "Please fill in all fields.")
            return

        try:
            scale = float(scale)
            images_per_batch = int(images_per_batch)

            if scale < 0 or images_per_batch <= 0:
                raise ValueError("Scale must be at least 0% and batch size must be positive.")

            self.run_scale_script(folder_path, scale / 100, images_per_batch)

        except ValueError as e:
            messagebox.showerror("Input Error", str(e))

    def run_scale_script(self, folder_path, scale, images_per_batch):
        """Run the scale.py script with the provided arguments."""
        command = ['python', 'scale.py', folder_path, str(scale), str(images_per_batch)]
        
        try:
            # Count images to process for progress bar
            image_files = [
                filename for filename in os.listdir(folder_path)
                if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp'))
            ]
            self.total_images = len(image_files)
            if self.total_images == 0:
                raise ValueError("No valid images found in the selected folder.")

            # Run the scaling process
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            # Monitor the process and update the progress bar
            self.processed_images = 0
            while process.poll() is None:
                output = process.stdout.readline()
                if output:
                    print(output.strip())
                    if "Scaled and saved" in output:
                        self.processed_images += 1
                        self.progress_queue.put(self.processed_images)
                # Sleep to avoid busy-waiting
                self.root.update_idletasks()

            # Final update after process completes
            self.progress_queue.put(None)

            messagebox.showinfo("Success", "Images have been scaled successfully!")

        except subprocess.CalledProcessError as e:
            messagebox.showerror("Error", f"An error occurred while scaling images:\n{e}")
        except ValueError as e:
            messagebox.showerror("Error", str(e))

    def update_progress_from_queue(self):
        """Update the progress bar based on the queue."""
        while True:
            processed_images = self.progress_queue.get()
            if processed_images is None:
                break
            if self.total_images > 0:
                progress = (processed_images / self.total_images) * 100
                self.progress_bar['value'] = progress
                self.root.update_idletasks()  # Refresh the GUI

    def update_scale_from_slider(self, value):
        """Update the scale entry box when the slider is moved."""
        self.scale_entry.delete(0, tk.END)
        self.scale_entry.insert(0, value)

    def update_scale_from_entry(self, event=None):
        """Update the slider when the entry box is changed."""
        try:
            value = int(self.scale_entry.get())
            if 0 <= value <= 200:
                self.scale_slider.set(value)
            else:
                raise ValueError
        except ValueError:
            messagebox.showwarning("Invalid Input", "Please enter a valid scale percentage (0-200).")
            self.scale_entry.delete(0, tk.END)
            self.scale_entry.insert(0, 0)  # Set to 0 on invalid input
            self.scale_slider.set(0)  # Update slider to 0

    def update_batch_from_slider(self, value):
        """Update the batch entry box when the slider is moved."""
        self.batch_entry.delete(0, tk.END)
        self.batch_entry.insert(0, value)

    def update_batch_from_entry(self, event=None):
        """Update the slider when the entry box is changed."""
        try:
            value = int(self.batch_entry.get())
            if 1 <= value <= 500:
                self.batch_slider.set(value)
            else:
                raise ValueError
        except ValueError:
            messagebox.showwarning("Invalid Input", "Please enter a valid batch size (1-500).")
            self.batch_entry.delete(0, tk.END)
            self.batch_entry.insert(0, 0)  # Set to 0 on invalid input
            self.batch_slider.set(1)  # Reset slider to minimum

if __name__ == "__main__":
    root = tk.Tk()
    app = ImageScalerApp(root)
    root.mainloop()