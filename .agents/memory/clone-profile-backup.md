---
name: Clone profile backup
description: Persistence rules for the .clone/.restore profile workflow.
---

The clone workflow must save the latest original profile before applying changes, including text metadata and an optional local photo file; restore must handle the no-photo case by removing the current photo.

**Why:** Profile restoration must survive process restarts and must not leave a cloned photo behind when the original profile had no photo.

**How to apply:** Keep metadata and photo backup files private and ignored, write temporary files on the same filesystem as their destination for atomic replacement, and abort clone if the original photo cannot be backed up.