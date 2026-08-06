---
name: IBEKS Control Panel architecture
description: Control Panel lifecycle, Theme Engine, and SQLite compatibility boundaries.
---

Control Panel Tahap 1 berada sebagai plugin terpisah dan memakai registry handler di loader untuk enable/disable/reload tanpa mengubah kontrak `setup(client)` plugin lama. Konfigurasi baru dimigrasikan ke SQLite tanpa menghapus tabel lama.

**Why:** Fitur tahap berikutnya harus bisa mengelola plugin yang sudah ada tanpa memindahkan atau menulis ulang struktur plugin, sementara status konfigurasi harus bertahan melewati restart.

**How to apply:** Tambahkan menu/fitur baru melalui helper Control Panel dan Theme Engine. Pertahankan `.plugins` lama; command baru memakai namespace `.plugin`, `.theme`, `.dashboard`/`.stats`, `.settings`, dan `.panel`.