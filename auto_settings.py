import os
import re
import sys
import winreg
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox

# Registry Setup Variables
root_key = winreg.HKEY_CURRENT_USER
subkey_path = r"SOFTWARE\JavaSoft\Prefs\ninjabrainbot"

sens = "sensitivity"
boattype = "default_boat_type"
mcver = "mc_version"
angleadjustdisplay = "angle_adjustment_display_type"
angleadjusttype = "angle_adjustment_type"
stddev = "sigma_boat"
boaterror = "boat_error"
crosscorrection = "crosshair_correction"
resheight = "resolution_height"
enableboateye = "use_precise_angle"

sens2 = "0.02291165"  # godsens
boattype2 = "2"  # greenboat
mcver2 = "0"  # 1.16.1
angleadjustdisplay2 = "1"  # Number of adjustments
angleadjusttype2 = "1"  # Tall resolution
stddev2 = "7.0/E-4"  # 0.0007
boaterror2 = "0.03"
crosscorrection2 = "0.0"
resheight2 = "16384.0"
enableboateye2 = "true"


def calculate_toolscreen_sens(old_sens: float, current_ts_sens: float = 1.0) -> float:
    """Calculates Toolscreen global sens."""
    new_sens = 0.02291165
    old_factor = (0.6 * old_sens + 0.2) ** 3
    new_factor = (0.6 * new_sens + 0.2) ** 3
    return (old_factor / new_factor) * current_ts_sens


def update_key_value(content: str, key: str, value: str, delimiter: str = "=") -> str:
    """Updates or inserts key/value pairs in text formats (options.txt, TOML, JSON)."""
    if delimiter == "=":
        pattern = rf'^\s*{re.escape(key)}\s*=.*$'
        replacement = f"{key} = {value}"
    elif delimiter == ":":
        pattern = rf'^\s*{re.escape(key)}:.*$'
        replacement = f"{key}:{value}"
    else:
        pattern = rf'({re.escape(key)}\s*:\s*)[^,\n]+'
        replacement = f'{key}: {value}'

    if re.search(pattern, content, flags=re.MULTILINE):
        return re.sub(pattern, replacement, content, flags=re.MULTILINE)
    else:
        return content + f"\n{replacement}"


def resolve_file_case_insensitive(directory: Path, filename: str) -> Path:
    """Finds a file inside the directory."""
    if not directory.exists():
        return directory / filename
    for file in directory.iterdir():
        if file.name.lower() == filename.lower():
            return file
    return directory / filename


def main():
    root = tk.Tk()
    root.withdraw()

    # Determine default initial directory for the folder picker
    user_home = Path.home()
    prism_instances_dir = user_home / "AppData" / "Roaming" / "PrismLauncher" / "instances"
    roaming_dir = user_home / "AppData" / "Roaming"

    if prism_instances_dir.exists():
        initial_dir = prism_instances_dir
    elif roaming_dir.exists():
        initial_dir = roaming_dir
    else:
        initial_dir = user_home

    prompt_message = 'Please go into your instance folder and click "Select Folder"'

    # Show message box before opening file explorer
    messagebox.showinfo("Select Instance Folder", prompt_message)

    # 1. Prompt folder selection
    selected_dir = filedialog.askdirectory(
        title=prompt_message,
        initialdir=str(initial_dir)
    )
    if not selected_dir:
        print("No directory selected. Exiting...")
        sys.exit(0)

    # Verify registry, file locations, permissions, and parameters before writing
    # Pre-check 1: Ninjabrain Bot Registry key access
    try:
        with winreg.OpenKey(root_key, subkey_path, 0, winreg.KEY_SET_VALUE) as key:
            pass
    except FileNotFoundError:
        messagebox.showerror("Validation Error", f"Registry path 'HKCU\\{subkey_path}' does not exist.")
        sys.exit(1)
    except PermissionError:
        messagebox.showerror("Validation Error", "Permission denied when accessing Windows Registry.")
        sys.exit(1)

    # Pre-check 2: Minecraft options.txt directory & existence
    base_dir = Path(selected_dir)
    if (base_dir / "options.txt").exists() or base_dir.name.lower() in ["minecraft", ".minecraft"]:
        mc_dir = base_dir
    else:
        mc_dir = resolve_file_case_insensitive(base_dir, "minecraft")

    options_file = mc_dir / "options.txt"
    if not mc_dir.exists() or not options_file.exists():
        messagebox.showerror(
            "Validation Error",
            f"Could not find valid 'options.txt' inside:\n{selected_dir}"
        )
        sys.exit(1)

    # Pre-check 3: Verify mouseSensitivity inside options.txt
    try:
        options_text = options_file.read_text(encoding="utf-8")
    except Exception as e:
        messagebox.showerror("Validation Error", f"Failed to read 'options.txt': {e}")
        sys.exit(1)

    sens_match = re.search(r"^mouseSensitivity:(.+)$", options_text, re.MULTILINE)
    if not sens_match:
        messagebox.showerror("Validation Error", "Could not find 'mouseSensitivity:' in options.txt")
        sys.exit(1)

    try:
        old_mc_sens = float(sens_match.group(1).strip())
    except ValueError:
        messagebox.showerror("Validation Error", "Invalid numerical value for mouseSensitivity in options.txt")
        sys.exit(1)

    # Pre-check 4: Toolscreen config resolution & access
    ts_config_dir = user_home / ".config" / "Toolscreen"
    profiles_toml = resolve_file_case_insensitive(ts_config_dir, "profiles.toml")

    target_toml_file = None
    if profiles_toml.exists():
        try:
            profiles_text = profiles_toml.read_text(encoding="utf-8")
            active_match = re.search(
                r'^\s*activeProfile\s*=\s*["\']?([^"\']+)["\']?',
                profiles_text,
                re.MULTILINE
            )
            if active_match:
                profile_name = active_match.group(1).strip()
                if not profile_name.endswith(".toml"):
                    profile_name += ".toml"
                target_toml_file = resolve_file_case_insensitive(ts_config_dir / "profiles", profile_name)
        except Exception as e:
            messagebox.showerror("Validation Error", f"Failed to read Toolscreen profiles.toml: {e}")
            sys.exit(1)

    if not target_toml_file or not target_toml_file.exists():
        target_toml_file = resolve_file_case_insensitive(ts_config_dir, "Config.toml")

    if not target_toml_file.exists():
        messagebox.showerror("Validation Error", f"Target Toolscreen config file not found:\n{target_toml_file}")
        sys.exit(1)

    # Pre-check 5: Read current Toolscreen sensitivity
    current_ts_sens = 1.0
    try:
        ts_content = target_toml_file.read_text(encoding="utf-8")
        ts_match = re.search(r'^\s*mouseSensitivity\s*=\s*([0-9.]+)', ts_content, re.MULTILINE)
        if ts_match:
            current_ts_sens = float(ts_match.group(1))
    except Exception as e:
        messagebox.showerror("Validation Error", f"Failed reading Toolscreen sensitivity from {target_toml_file}:\n{e}")
        sys.exit(1)


    # All checks passed; proceeding with updates

    # 1. Update Registry settings
    try:
        with winreg.OpenKey(root_key, subkey_path, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, sens, 0, winreg.REG_SZ, sens2)
            winreg.SetValueEx(key, boattype, 0, winreg.REG_SZ, boattype2)
            winreg.SetValueEx(key, mcver, 0, winreg.REG_SZ, mcver2)
            winreg.SetValueEx(key, angleadjustdisplay, 0, winreg.REG_SZ, angleadjustdisplay2)
            winreg.SetValueEx(key, angleadjusttype, 0, winreg.REG_SZ, angleadjusttype2)
            winreg.SetValueEx(key, stddev, 0, winreg.REG_SZ, stddev2)
            winreg.SetValueEx(key, boaterror, 0, winreg.REG_SZ, boaterror2)
            winreg.SetValueEx(key, crosscorrection, 0, winreg.REG_SZ, crosscorrection2)
            winreg.SetValueEx(key, resheight, 0, winreg.REG_SZ, resheight2)
            winreg.SetValueEx(key, enableboateye, 0, winreg.REG_SZ, enableboateye2)
        print("Updated Registry values.")
    except Exception as e:
        messagebox.showerror("Execution Error", f"Failed updating Registry: {e}")
        sys.exit(1)

    # 2. Update Toolscreen Config
    toolscreen_sens = calculate_toolscreen_sens(old_mc_sens, current_ts_sens)
    updated_ts_content = update_key_value(ts_content, "mouseSensitivity", f"{toolscreen_sens:.8f}", delimiter="=")
    target_toml_file.write_text(updated_ts_content, encoding="utf-8")
    print(f"Updated Toolscreen sens in: {target_toml_file}")

    # 3. Update options.txt in minecraft directory
    options_content = options_file.read_text(encoding="utf-8")
    options_content = update_key_value(options_content, "mouseSensitivity", "0.02291165", delimiter=":")
    options_content = update_key_value(options_content, "rawMouseInput", "true", delimiter=":")
    options_file.write_text(options_content, encoding="utf-8")
    print(f"Updated options.txt in: {options_file}")

    # 4. Check & update standardsettings.json in config/mcsr if present
    mcsr_settings = mc_dir / "config" / "mcsr" / "standardsettings.json"
    if mcsr_settings.exists():
        json_content = mcsr_settings.read_text(encoding="utf-8")
        json_content = re.sub(r'("mouseSensitivity"\s*:\s*)[^,\n]+', r'\g<1>0.02291165', json_content)
        json_content = re.sub(r'("rawMouseInput"\s*:\s*)[^,\n]+', r'\g<1>true', json_content)
        mcsr_settings.write_text(json_content, encoding="utf-8")
        print("Updated standardsettings.json")

    messagebox.showinfo("Success", "Settings set successfully!")


if __name__ == "__main__":
    main()