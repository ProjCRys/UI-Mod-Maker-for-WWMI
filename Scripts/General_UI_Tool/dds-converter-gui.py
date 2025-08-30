import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import subprocess
import os
import threading
import time

class Converter:
    def __init__(self, root):
        self.root = root
        self.root.title("DDS Converter GUI")
        self.root.geometry("600x400")  # Increased height to accommodate new elements
        self.root.minsize(600, 400)

        self.root.columnconfigure(0, weight=1)
        self.root.columnconfigure(1, weight=1)

        self.create_widgets()

    def create_widgets(self):
        # Input folder selection
        self.input_label = tk.Label(self.root, text="Input Folder:")
        self.input_label.grid(row=0, column=0, padx=10, pady=10, sticky="e")
        self.input_entry = tk.Entry(self.root, width=50)
        self.input_entry.grid(row=0, column=1, padx=10, pady=10)
        self.input_button = tk.Button(self.root, text="Browse", command=self.select_input_folder)
        self.input_button.grid(row=0, column=2, padx=10, pady=10)

        # Output folder selection
        self.output_label = tk.Label(self.root, text="Output Folder:")
        self.output_label.grid(row=1, column=0, padx=10, pady=10, sticky="e")
        self.output_entry = tk.Entry(self.root, width=50)
        self.output_entry.grid(row=1, column=1, padx=10, pady=10)
        self.output_button = tk.Button(self.root, text="Browse", command=self.select_output_folder)
        self.output_button.grid(row=1, column=2, padx=10, pady=10)

        # GPU ID input
        self.gpu_label = tk.Label(self.root, text="GPU ID:")
        self.gpu_label.grid(row=2, column=0, padx=10, pady=10, sticky="e")
        self.gpu_entry = tk.Entry(self.root, width=20)
        self.gpu_entry.grid(row=2, column=1, padx=10, pady=10)
        
        # Help button for GPU ID
        self.gpu_help_button = tk.Button(self.root, text="?", command=self.show_gpu_info)
        self.gpu_help_button.grid(row=2, column=2, padx=10, pady=10)

        # Run conversion button
        self.convert_button = tk.Button(self.root, text="Convert", command=self.run_conversion)
        self.convert_button.grid(row=3, column=1, padx=10, pady=20)

        # Progress bar
        self.progress_bar = ttk.Progressbar(self.root, orient="horizontal", length=400, mode="determinate")
        self.progress_bar.grid(row=4, column=0, columnspan=3, padx=10, pady=20)

    def show_gpu_info(self):
        """Show information about how to get the GPU ID."""
        messagebox.showinfo("GPU ID Information",
                            "To find your GPU ID:\n1. Open Task Manager.\n2. Go to the Performance tab.\n3. Select your GPU on the left side.\n4. The GPU ID will be displayed in the details.")

    def select_input_folder(self):
        """Open a dialog to select the input folder."""
        folder_selected = filedialog.askdirectory(title="Select Input Folder")
        self.input_entry.delete(0, tk.END)
        self.input_entry.insert(0, folder_selected)

    def select_output_folder(self):
        """Open a dialog to select the output folder."""
        folder_selected = filedialog.askdirectory(title="Select Output Folder")
        self.output_entry.delete(0, tk.END)
        self.output_entry.insert(0, folder_selected)

    def run_conversion(self):
        """Run the conversion process with the provided input and output folders."""
        input_folder = self.input_entry.get()
        output_folder = self.output_entry.get()
        gpu_id = self.gpu_entry.get()  # Get GPU ID from the entry

        if not input_folder or not output_folder or not gpu_id:
            print("Error: Please specify both input and output folders and the GPU ID.")
            return

        # Disable the convert button and reset the progress bar
        self.convert_button.config(state=tk.DISABLED)
        self.progress_bar['value'] = 0
        self.root.update_idletasks()

        # Get the total number of files in batch folders, excluding the output folder
        total_files = self.count_total_files(input_folder, output_folder)
        print(f"Total files to convert: {total_files}")

        # Start conversion in a new thread
        threading.Thread(target=self.execute_conversion, args=(input_folder, output_folder, gpu_id, total_files)).start()

    def count_total_files(self, input_folder, output_folder):
        """Count the total number of files in all batch folders, excluding the output folder."""
        total_files = 0
        for batch_folder in os.listdir(input_folder):
            batch_path = os.path.join(input_folder, batch_folder)
            if os.path.isdir(batch_path) and batch_folder.startswith("batch"):
                # Count files in the batch folder
                total_files += len(os.listdir(batch_path))
        return total_files

    def execute_conversion(self, input_folder, output_folder, gpu_id, total_files):
        """Execute the conversion and update progress."""
        command = ["python", "General_UI_Tool/dds-converter.py", input_folder, output_folder, "--gpu", gpu_id]
        
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        # Start a thread for updating progress
        threading.Thread(target=self.update_progress, args=(output_folder, total_files)).start()

        # Monitor the output
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                print(output.strip())

        # Ensure completion
        process.wait()
        if process.returncode == 0:
            print("Conversion completed successfully.")
        else:
            print(f"Error during conversion: {process.stderr.read()}")

        # Re-enable the convert button and finalize progress
        self.convert_button.config(state=tk.NORMAL)
        self.progress_bar['value'] = 100

    def update_progress(self, output_folder, total_files):
        """Update the progress bar based on the number of converted files."""
        while True:
            converted_files = self.count_converted_files(output_folder)  # Count converted files
            if total_files > 0:
                progress = (converted_files / total_files) * 100  # Calculate percentage
                self.progress_bar['value'] = progress
            if self.progress_bar['value'] >= 100:
                break
            self.root.update_idletasks()  # Update the GUI
            time.sleep(0.1)  # Pause for a second before checking again

    def count_converted_files(self, output_folder):
        """Count the number of files in the output folder."""
        return len(os.listdir(output_folder))

# Create the main application window
root = tk.Tk()
converter = Converter(root)
root.mainloop()
