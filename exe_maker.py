import os
import sys
import subprocess
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog

# --- Configuration ---
RESOURCE_EXTENSIONS = {
    '.png', '.jpg', '.jpeg', '.gif', '.ico', # Images
    '.mp3', '.wav', '.ogg',                  # Audio
    '.mp4', '.mov', '.avi',                  # Video
    '.json', '.xml', '.csv', '.txt',         # Data files
    '.ttf', '.otf',                          # Fonts
    '.html', '.css', '.js'                   # Web files
}
PROBLEM_PACKAGES = ['pathlib']

def run_pip_command(command, show_output=True):
    """Runs a pip command using the current Python interpreter."""
    try:
        process = subprocess.Popen(
            [sys.executable, "-m", "pip"] + command,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding='utf-8', errors='replace'
        )
        if show_output:
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    print(output.strip())
        process.wait()
        return process.poll() == 0
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"Error running pip command: {e}")
        return False

def check_and_install_pyinstaller():
    """Checks if PyInstaller is installed and prompts to install it if not."""
    print("--- Checking for PyInstaller ---")
    try:
        subprocess.run([sys.executable, "-m", "pip", "show", "pyinstaller"], check=True, capture_output=True)
        print("PyInstaller is already installed.")
        return True
    except subprocess.CalledProcessError:
        print("PyInstaller is not found.")
        root = tk.Tk(); root.withdraw()
        if messagebox.askyesno("Installation Required", "PyInstaller is not installed. Do you want to install it now?"):
            print("Installing PyInstaller...")
            if run_pip_command(["install", "pyinstaller"]):
                print("PyInstaller installed successfully.")
                return True
            else:
                messagebox.showerror("Installation Failed", "Failed to install PyInstaller. Please check the console and install it manually:\npip install pyinstaller")
                return False
        else:
            print("Installation cancelled by user.")
            return False

def check_and_install_pillow():
    """Checks if Pillow is installed and prompts to install it if not (for icon conversion)."""
    print("\n--- Checking for Pillow (for icon conversion) ---")
    try:
        subprocess.run([sys.executable, "-m", "pip", "show", "Pillow"], check=True, capture_output=True)
        print("Pillow is already installed.")
        return True
    except subprocess.CalledProcessError:
        print("Pillow is not found.")
        root = tk.Tk(); root.withdraw()
        if messagebox.askyesno("Installation Required", "The 'Pillow' library is required for converting images to .ico files.\n\nDo you want to install it now?"):
            print("Installing Pillow...")
            if run_pip_command(["install", "Pillow"]):
                print("Pillow installed successfully.")
                return True
            else:
                messagebox.showerror("Installation Failed", "Failed to install Pillow. Please check the console and install it manually:\npip install Pillow")
                return False
        else:
            print("Installation cancelled by user. Icon functionality will be disabled.")
            return False

def select_and_convert_logo():
    """Asks user to select a logo, ensures Pillow is installed, converts it, and returns the path."""
    root = tk.Tk(); root.withdraw()
    if not messagebox.askyesno("Custom Icon", "Do you want to add a custom icon to the .exe file?"):
        return None

    if not check_and_install_pillow():
        messagebox.showwarning("Icon Skipped", "Pillow installation failed or was cancelled.\nThe build will continue without a custom icon.")
        return None

    from PIL import Image

    image_path = filedialog.askopenfilename(
        title="Select an image for the icon",
        filetypes=(("Image Files", "*.png *.jpg *.jpeg *.gif *.bmp"), ("All files", "*.*"))
    )

    if not image_path:
        print("No icon file selected. Continuing without a custom icon.")
        return None

    output_icon_path = "temp_icon.ico"
    print(f"\n--- Converting '{os.path.basename(image_path)}' to '{output_icon_path}' ---")

    try:
        with Image.open(image_path) as img:
            img.save(output_icon_path, format='ICO', sizes=[(16,16), (32,32), (48,48), (64,64), (128,128), (256,256)])
        print("Icon conversion successful.")
        return output_icon_path
    except Exception as e:
        messagebox.showerror("Icon Conversion Failed", f"Could not convert the image to an icon file.\n\nError: {e}\n\nThe build will continue without a custom icon.")
        print(f"ERROR: Icon conversion failed: {e}")
        return None

def check_and_fix_problematic_packages():
    """Checks for and offers to remove packages that conflict with PyInstaller."""
    print("\n--- Checking for known problematic packages ---")
    all_ok = True
    for package_name in PROBLEM_PACKAGES:
        try:
            subprocess.run([sys.executable, "-m", "pip", "show", package_name], check=True, capture_output=True)
            print(f"Found conflicting package: '{package_name}'")
            root = tk.Tk(); root.withdraw()
            if messagebox.askyesno("Conflict Detected", f"The package '{package_name}' is installed and known to cause issues with PyInstaller.\n\nIt's an obsolete version that conflicts with Python's standard library.\n\nMay I uninstall it for you? (This is the recommended action)"):
                print(f"Uninstalling '{package_name}'...")
                if not run_pip_command(["uninstall", "-y", package_name]):
                    messagebox.showerror("Uninstall Failed", f"Could not uninstall '{package_name}'. Please uninstall it manually:\npip uninstall {package_name}")
                    all_ok = False
                else:
                    print(f"'{package_name}' uninstalled successfully.")
            else:
                messagebox.showwarning("Build Warning", "You chose not to uninstall a conflicting package. The build may fail.")
                all_ok = False
        except subprocess.CalledProcessError:
            print(f"Package '{package_name}' not found (Good).")
            continue
    return all_ok

def handle_setup_file(project_root):
    """Parses setup.bat for pip install commands and offers to install them."""
    setup_bat_path = os.path.join(project_root, "setup.bat")
    if not os.path.exists(setup_bat_path):
        parent_dir = os.path.dirname(project_root)
        setup_bat_path_parent = os.path.join(parent_dir, "setup.bat")
        if os.path.exists(setup_bat_path_parent):
            setup_bat_path = setup_bat_path_parent
        else:
            return True

    print(f"\n--- Found setup.bat in {os.path.dirname(setup_bat_path)} ---")
    packages_to_install = set()
    try:
        with open(setup_bat_path, 'r') as f:
            for line in f:
                clean_line = line.strip().lower()
                if "pip install" in clean_line:
                    parts = clean_line.split()
                    install_index = parts.index("install")
                    for part in parts[install_index + 1:]:
                        if not part.startswith('-'):
                            packages_to_install.add(part)
    except Exception as e:
        messagebox.showwarning("Warning", f"Could not read or parse setup.bat: {e}")
        return True

    if not packages_to_install: return True

    package_list_str = "\n - ".join(sorted(list(packages_to_install)))
    root = tk.Tk(); root.withdraw()
    if messagebox.askyesno("Dependencies Found", f"Found the following packages in setup.bat:\n\n - {package_list_str}\n\nDo you want to install/update them now?"):
        print("Installing dependencies from setup.bat...")
        if not run_pip_command(["install"] + list(packages_to_install)):
            messagebox.showerror("Installation Failed", "Failed to install dependencies. Please check the console and install them manually.")
            return False
        print("Dependencies installed successfully.")
    return True

def select_main_script():
    """Opens a file dialog to select the main Python script."""
    root = tk.Tk(); root.withdraw()
    messagebox.showinfo("Select Script", "Please select the main Python script of your project (e.g., main.py).")
    filepath = filedialog.askopenfilename(title="Select your main Python script", filetypes=(("Python Files", "*.py"), ("All files", "*.*")))
    if not filepath: sys.exit("No script selected. Exiting.")
    return filepath

def get_exe_name(script_path):
    """Asks the user for a desired name for the output exe."""
    root = tk.Tk(); root.withdraw()
    base_name = os.path.basename(script_path).rsplit('.', 1)[0]
    
    user_input = simpledialog.askstring(
        "Executable Name",
        "Enter the desired name for the final executable (without .exe):",
        initialvalue=base_name
    )
    
    if not user_input:
        print(f"No name entered. Defaulting to '{base_name}'.")
        return base_name
        
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        user_input = user_input.replace(char, '')

    if user_input.lower().endswith('.exe'):
        user_input = user_input[:-4]
        
    print(f"Using executable name: '{user_input}'")
    return user_input

def scan_for_resources(project_root):
    """Scans the project directory for resource files to bundle."""
    print(f"\n--- Scanning for resource files in: {project_root} ---")
    data_files = []
    for root, _, files in os.walk(project_root):
        if 'venv' in root or '__pycache__' in root or 'build' in root or 'dist' in root:
            continue
        for file in files:
            if any(file.lower().endswith(ext) for ext in RESOURCE_EXTENSIONS):
                source_path = os.path.join(root, file)
                relative_path = os.path.relpath(source_path, project_root)
                destination_folder = os.path.dirname(relative_path)
                if destination_folder == "":
                    destination_folder = "."
                data_files.append((source_path, destination_folder))
                print(f"  > Found resource: {relative_path}")
    return data_files

def run_pyinstaller(command):
    """Executes the PyInstaller command and streams the output."""
    print("\n--- Running PyInstaller ---")
    print(f"Command: {' '.join(command)}\n")
    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace')
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None: break
            if output: print(output.strip())
        return process.poll() == 0
    except FileNotFoundError:
        print("ERROR: 'pyinstaller' command not found. Is it installed and in your PATH?")
        return False

def main():
    """Main function to drive the EXE creation process."""
    if not check_and_install_pyinstaller(): sys.exit(1)
    if not check_and_fix_problematic_packages(): sys.exit(1)

    main_script_path = select_main_script()
    project_root = os.path.dirname(main_script_path)
    
    exe_name = get_exe_name(main_script_path)
    
    if not handle_setup_file(project_root):
        print("Dependency installation failed. Aborting build.")
        sys.exit(1)

    root = tk.Tk(); root.withdraw()
    one_file_mode = messagebox.askyesno("Build Option", "Create a single .exe file?\n\n(Note: Single files may start slower.)")
    is_gui_app = messagebox.askyesno("Build Option", "Is this a GUI application?\n\n(Select 'Yes' to hide the console window.)")
    
    icon_path = select_and_convert_logo()
    resources = scan_for_resources(project_root)
    
    pyinstaller_command = ["pyinstaller", main_script_path, "--noconfirm", "--name", exe_name]
    if one_file_mode: pyinstaller_command.append("--onefile")
    if is_gui_app: pyinstaller_command.append("--windowed")
    if icon_path: pyinstaller_command.extend(["--icon", icon_path])
        
    for source, dest in resources:
        arg = f"{source}{os.pathsep}{dest}"
        pyinstaller_command.extend(["--add-data", arg])
        
    build_success = run_pyinstaller(pyinstaller_command)

    if build_success:
        print("\n--- Build successful, preparing to move output ---")
        
        dist_path = os.path.join(os.getcwd(), 'dist')
        source_item_name = f"{exe_name}.exe" if one_file_mode else exe_name
        source_path = os.path.join(dist_path, source_item_name)
        
        # *** MODIFIED PART ***
        # The destination is now the same directory as the selected main script.
        dest_path = os.path.join(project_root, source_item_name)
        
        try:
            if os.path.exists(dest_path):
                if messagebox.askyesno("Overwrite Confirmation", f"The file or folder '{source_item_name}' already exists in the destination directory:\n\n{project_root}\n\nDo you want to replace it?"):
                    print(f"Removing existing item: '{dest_path}'...")
                    if os.path.isdir(dest_path): shutil.rmtree(dest_path)
                    else: os.remove(dest_path)
                else:
                    print("Move cancelled. Your file remains in the 'dist' folder.")
                    print("\n" + "="*40 + "\n✅ BUILD SUCCESSFUL! ✅\n" + f"Your executable is in: {dist_path}" + "\n" + "="*40)
                    if icon_path and os.path.exists(icon_path): os.remove(icon_path)
                    return

            print(f"Moving '{source_path}' to '{project_root}'...")
            shutil.move(source_path, dest_path)
            
            print("\n" + "="*40 + "\n✅ BUILD SUCCESSFUL! ✅\n" + f"Your application '{source_item_name}' has been moved to:\n{project_root}" + "\n" + "="*40)

            if messagebox.askyesno("Cleanup", "Build successful. Remove temporary build files (including the now-empty 'dist' folder)?"):
                print("Cleaning up...")
                spec_file = f"{exe_name}.spec"
                if os.path.exists("build"): shutil.rmtree("build")
                if os.path.exists("dist"): shutil.rmtree("dist")
                if os.path.exists(spec_file): os.remove(spec_file)
                print("Cleanup complete.")

        except Exception as e:
            print(f"\nERROR: An error occurred while moving the output: {e}")
            print("The build was successful, but the output could not be moved.")
            print(f"Your executable can be found in: {dist_path}")

    else:
        print("\n" + "="*40 + "\n❌ BUILD FAILED! ❌\n" + "Please check the log above for errors." + "\n" + "="*40)
    
    if icon_path and os.path.exists(icon_path):
        print(f"Cleaning up temporary icon file: {icon_path}")
        os.remove(icon_path)

if __name__ == "__main__":
    main()