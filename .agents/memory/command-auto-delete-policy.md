---
name: Command auto-delete policy
description: Command Userbot harus mempertahankan riwayat chat kecuali masuk allowlist auto-delete terpusat.
---

Command Userbot tidak boleh menghapus pesan pengguna secara global; hanya command yang sengaja dimasukkan ke allowlist terpusat yang boleh dihapus.

**Why:** Pengguna ingin riwayat command tetap terlihat dan daftar pengecualian mudah dikelola tanpa mengubah setiap plugin.

**How to apply:** Saat menambah atau mengubah command yang perlu auto-delete, ubah allowlist utilitas bersama, bukan menambahkan perilaku penghapusan langsung di plugin.