import subprocess
import sys
import time

def run_bots():
    print("🚀 Menyalakan Ubot dan Bot Anonim secara bersamaan...")
    
    # Menjalankan ubot (sesuaikan path-nya jika file utama ubot ada di dalam folder userbot)
    # Berdasarkan struktur folder lu, biasanya ubot dijalankan lewat userbot/main.py atau loader.py
    ubot_process = subprocess.Popen([sys.executable, "userbot/main.py"])
    
    # Beri jeda 2 detik biar ubot siap dulu
    time.sleep(2)
    
    # Menjalankan bot anonim lu
    anon_process = subprocess.Popen([sys.executable, "anonbot/anon_bot.py"])
    
    try:
        # Menjaga proses tetap hidup
        ubot_process.wait()
        anon_process.wait()
    except KeyboardInterrupt:
        print("\n🛑 Mematikan semua bot...")
        ubot_process.terminate()
        anon_process.terminate()

if __name__ == "__main__":
    run_bots()
    
