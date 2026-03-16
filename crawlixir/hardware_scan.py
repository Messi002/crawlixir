"""Hardware scanner - figures out which Ollama model your machine can handle."""

import platform
import math
import subprocess
import re


def convert_size(size_bytes):
    if size_bytes == 0:
        return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}"


def get_gpu_info():
    """Detect GPU across platforms."""
    system = platform.system()
    gpus = []

    # Apple Silicon (macOS)
    if system == "Darwin":
        try:
            out = subprocess.check_output(
                ["sysctl", "-n", "machdep.cpu.brand_string"], text=True
            ).strip()
            if "Apple" in out:
                gpus.append({"name": f"{out} (Apple Silicon - Unified Memory)", "vram": "shared"})
        except Exception:
            pass

    # NVIDIA GPU
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=name,memory.total,memory.free", "--format=csv,noheader,nounits"],
            text=True,
        ).strip()
        for line in out.splitlines():
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 3:
                gpus.append({
                    "name": parts[0],
                    "vram_total_mb": int(parts[1]),
                    "vram_free_mb": int(parts[2]),
                })
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass

    # AMD GPU (Linux ROCm)
    if system == "Linux" and not gpus:
        try:
            out = subprocess.check_output(["rocm-smi", "--showmeminfo", "vram"], text=True)
            gpus.append({"name": "AMD GPU (ROCm)", "info": out.strip()})
        except (FileNotFoundError, subprocess.CalledProcessError):
            pass

    # Fallback: check lspci for GPU info (Linux)
    if system == "Linux" and not gpus:
        try:
            out = subprocess.check_output(["lspci"], text=True)
            for line in out.splitlines():
                if any(k in line.lower() for k in ["vga", "3d", "display"]):
                    gpus.append({"name": line.split(": ", 1)[-1], "vram": "unknown"})
        except (FileNotFoundError, subprocess.CalledProcessError):
            pass

    return gpus


def get_ram():
    """Get total and available RAM in bytes, cross-platform."""
    system = platform.system()

    if system == "Darwin":
        try:
            total = int(subprocess.check_output(["sysctl", "-n", "hw.memsize"], text=True).strip())
            vm = subprocess.check_output(["vm_stat"], text=True)
            free_pages = int(re.search(r"Pages free:\s+(\d+)", vm).group(1))
            available = free_pages * 4096
            return total, available
        except Exception:
            pass

    if system == "Linux":
        try:
            with open("/proc/meminfo") as f:
                info = f.read()
            total = int(re.search(r"MemTotal:\s+(\d+)", info).group(1)) * 1024
            available = int(re.search(r"MemAvailable:\s+(\d+)", info).group(1)) * 1024
            return total, available
        except Exception:
            pass

    # Windows
    if system == "Windows":
        try:
            import ctypes
            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]
            stat = MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(stat)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
            return stat.ullTotalPhys, stat.ullAvailPhys
        except Exception:
            pass

    return 0, 0


def get_cpu_info():
    """Get CPU core count."""
    import os
    physical = os.cpu_count()
    return physical or 0


def recommend_model(ram_gb, gpu_vram_mb=0, apple_silicon=False):
    """Recommend Ollama models based on hardware."""
    models = []

    effective_memory = ram_gb if apple_silicon else (gpu_vram_mb / 1024 if gpu_vram_mb else ram_gb)

    if effective_memory >= 48:
        models.append(("llama3.1:70b", "70B", "~40GB", "Top-tier, if you have the hardware"))
    if effective_memory >= 24:
        models.append(("qwen2.5:32b", "32B", "~20GB", "Good at coding and structured output"))
        models.append(("command-r", "35B", "~20GB", "Works well for RAG and tool use"))
    if effective_memory >= 16:
        models.append(("llama3.1:8b", "8B", "~4.7GB", "Solid all-rounder, writes well"))
        models.append(("mistral", "7B", "~4.1GB", "Fast, capable"))
    if effective_memory >= 8:
        models.append(("llama3.2", "3B", "~2.0GB", "Best tradeoff for most people"))
        models.append(("gemma2:2b", "2B", "~1.6GB", "Small but surprisingly capable"))
        models.append(("qwen2.5:3b", "3B", "~1.9GB", "Good at coding tasks"))
    if effective_memory >= 4:
        models.append(("llama3.2:1b", "1B", "~1.3GB", "Lightweight, fast on CPU"))
        models.append(("tinyllama", "1.1B", "~0.6GB", "Smallest option that still works"))

    return models


def scan():
    """Run full hardware scan and print recommendations."""
    print("=" * 50)
    print("CRAWLIXIR HARDWARE SCANNER")
    print("=" * 50)

    system = platform.system()
    print(f"\n  OS: {system} {platform.release()}")
    print(f"  Arch: {platform.machine()}")
    print(f"  CPU Cores: {get_cpu_info()}")

    total_ram, avail_ram = get_ram()
    ram_gb = total_ram / (1024 ** 3)
    print(f"  RAM: {convert_size(total_ram)} Total ({convert_size(avail_ram)} Available)")

    gpus = get_gpu_info()
    gpu_vram_mb = 0
    apple_silicon = False

    print("\n  GPU:")
    if not gpus:
        print("   No dedicated GPU detected. Models will run on CPU (slower but works).")
    else:
        for gpu in gpus:
            print(f"   {gpu['name']}")
            if "vram_total_mb" in gpu:
                print(f"   VRAM: {gpu['vram_total_mb']}MB Total ({gpu['vram_free_mb']}MB Free)")
                gpu_vram_mb = max(gpu_vram_mb, gpu["vram_total_mb"])
            if "shared" in str(gpu.get("vram", "")):
                apple_silicon = True
                print("   Unified Memory: Your full RAM is available for AI models.")

    models = recommend_model(ram_gb, gpu_vram_mb, apple_silicon)

    print("\n" + "=" * 50)
    print("RECOMMENDED MODELS:")
    print("=" * 50)

    if not models:
        print("  Less than 4GB RAM. Local models will struggle.")
        print("  You might want to look at cloud APIs instead.")
    else:
        print(f"\n{'Model':<25} {'Size':<8} {'Disk':<10} {'Notes'}")
        print("-" * 75)
        for cmd, size, disk, note in models:
            print(f"{cmd:<25} {size:<8} {disk:<10} {note}")

        top = models[-1] if ram_gb < 16 else [m for m in models if "tradeoff" in m[3]][0] if any("tradeoff" in m[3] for m in models) else models[0]
        print(f"\n  Quick start: ollama run {top[0]}")

    print(f"\n  Install Ollama: curl -fsSL https://ollama.com/install.sh | sh")
    print("=" * 50)


if __name__ == "__main__":
    scan()
