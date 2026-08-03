---
name: Voice Chat Manager panel
description: Voice Chat Userbot dikendalikan dari panel private Manager melalui IPC lokal.
---

Voice Chat harus mengirim hasil join ke private chat Manager dan menerima aksi tombol melalui IPC runtime; Userbot tidak mengirim status atau panel ke grup.

**Why:** Manager adalah panel kontrol tunggal, sementara setiap Userbot berjalan sebagai proses terisolasi sehingga callback Manager tidak dapat mengakses voice manager secara langsung.

**How to apply:** Pertahankan `.joinvc` sebagai satu-satunya command grup yang memulai proses, gunakan callback Manager untuk mic/leave/refresh, dan edit satu pesan panel yang sama.