# Employee Activity Tracker Dashboard Plan

## 1. Latar Belakang

Kebutuhan bisnisnya adalah membuat dashboard untuk memantau aktivitas karyawan lintas divisi dalam satu aplikasi lokal yang mudah dipakai oleh admin internal. Fokus utamanya bukan membangun service production-grade, tetapi membuat sistem yang:

- punya struktur database yang rapi
- punya schema yang jelas dan mudah dikembangkan
- punya admin page untuk input/edit data
- punya dashboard yang enak dibaca untuk monitoring aktivitas, progres, dan status pekerjaan
- bisa dijalankan lokal oleh tim analyst/ops tanpa kebutuhan DevOps yang berat

Dokumen ini sengaja mengarah ke solusi pragmatis: local-first, maintainable, dan cukup proper untuk demo, pilot internal, atau operasional skala kecil-menengah.

## 2. Goal Produk

Tujuan versi pertama:

- Menyimpan master data organisasi: divisi, karyawan, project/inisiatif, dan task/work item.
- Mencatat aktivitas kerja harian atau periodik per karyawan.
- Menampilkan status pekerjaan lintas divisi: `Not Started`, `In Progress`, `Blocked`, `Done`, `On Hold`.
- Memberi admin kemampuan tambah, edit, dan update status dari UI.
- Menyediakan dashboard ringkas untuk pimpinan atau coordinator.

## 3. Non-Goal

Hal berikut tidak menjadi fokus fase awal:

- SSO, RBAC kompleks, atau security hardening
- arsitektur microservice
- high availability / horizontal scaling
- audit/compliance enterprise
- real-time collaboration yang kompleks
- API publik untuk integrasi eksternal

Kalau nanti aplikasi ini diterima dan dipakai lebih luas, area tersebut bisa jadi fase berikutnya.

## 4. Prinsip Solusi

- Local-first: aplikasi berjalan di laptop atau server lokal kantor.
- Simple stack: pilih teknologi yang familiar dan cepat jadi.
- Database dulu rapi: schema harus cukup normalized supaya data tidak berantakan.
- Dashboard operasional: fokus ke pertanyaan bisnis, bukan hanya tabel mentah.
- CRUD admin lengkap untuk master data dan aktivitas.

## 5. Rekomendasi Stack

Karena kebutuhan utamanya adalah dashboard + admin input lokal, stack yang paling pragmatis:

- Frontend + admin UI: `Streamlit`
- ORM / database layer: `SQLAlchemy`
- Database lokal: `SQLite`
- Visualisasi: `Plotly`
- Validation schema: `Pydantic` atau schema ringan internal

Alasan:

- `Streamlit` cocok untuk data analyst, cepat dibuat, dan cukup bagus untuk internal tools.
- `SQLite` cukup untuk single-machine / small-team local usage.
- `SQLAlchemy` sudah tepat untuk menjaga schema tetap proper.
- Kalau nanti butuh naik level, migrasi ke `PostgreSQL` masih realistis.

## 6. User yang Akan Pakai

### 6.1 Admin / Operator

- tambah dan edit master data
- input aktivitas
- update status pekerjaan
- koreksi data yang salah

### 6.2 Manager / Lead Divisi

- lihat progres tim/divisi
- lihat blocker
- lihat beban kerja anggota tim

### 6.3 Head / Management

- lihat ringkasan lintas divisi
- bandingkan output, status, dan bottleneck

## 7. Scope Fitur V1

### 7.1 Master Data

- Division
- Employee
- Project / Initiative
- Work Item / Task
- Status reference

### 7.2 Activity Tracking

- input aktivitas per tanggal
- update progres pekerjaan
- catat blocker dan next action
- catat jam kerja atau effort estimate

### 7.3 Dashboard

- overview perusahaan / semua divisi
- ringkasan per divisi
- ringkasan per karyawan
- daftar task bermasalah / blocked
- progress project / initiative

### 7.4 Admin Tools

- form tambah/edit/delete data
- filter dan pencarian
- bulk upload CSV untuk master data atau activity log

## 8. Pertanyaan Bisnis yang Harus Bisa Dijawab

Dashboard minimal harus bisa menjawab:

- Divisi mana yang paling banyak task `Blocked`?
- Karyawan mana yang belum submit activity hari ini / minggu ini?
- Project mana yang progresnya paling lambat?
- Task apa saja yang overdue?
- Distribusi workload per divisi bagaimana?
- Dalam 7-30 hari terakhir, status kerja didominasi `Done`, `In Progress`, atau `Blocked`?

## 9. Desain Data Model

### 9.1 Entitas Utama

Entity yang direkomendasikan:

- `divisions`
- `employees`
- `projects`
- `work_items`
- `work_item_assignees`
- `activity_logs`
- `status_history`

### 9.2 Relasi Utama

- Satu `division` punya banyak `employees`.
- Satu `division` bisa punya banyak `projects`.
- Satu `project` punya banyak `work_items`.
- Satu `work_item` bisa di-assign ke satu atau lebih `employees`.
- Satu `employee` punya banyak `activity_logs`.
- Satu `work_item` bisa punya banyak `activity_logs`.
- Perubahan status penting disimpan di `status_history`.

## 10. Schema Database Awal

### 10.1 `divisions`

Tujuan: menyimpan master divisi lintas organisasi.

Kolom yang disarankan:

- `id` UUID / integer primary key
- `code` string, unique
- `name` string
- `description` text nullable
- `is_active` boolean
- `created_at`
- `updated_at`

### 10.2 `employees`

Tujuan: menyimpan data karyawan.

Kolom yang disarankan:

- `id` UUID / integer primary key
- `employee_code` string, unique
- `full_name` string
- `email` string nullable
- `job_title` string
- `division_id` foreign key -> `divisions.id`
- `manager_name` string nullable
- `employment_status` string
- `joined_date` date nullable
- `is_active` boolean
- `created_at`
- `updated_at`

Catatan:

- Untuk versi lokal, `manager_name` bisa disimpan sebagai text dulu.
- Nanti kalau mau lebih proper, bisa ditambah `manager_employee_id`.

### 10.3 `projects`

Tujuan: wadah inisiatif besar atau project lintas divisi.

Kolom yang disarankan:

- `id` UUID / integer primary key
- `project_code` string, unique
- `name` string
- `description` text nullable
- `owner_division_id` foreign key -> `divisions.id`
- `priority` string
- `status` string
- `start_date` date nullable
- `target_end_date` date nullable
- `created_at`
- `updated_at`

### 10.4 `work_items`

Tujuan: unit pekerjaan utama yang dipantau di dashboard.

Kolom yang disarankan:

- `id` UUID / integer primary key
- `project_id` foreign key nullable -> `projects.id`
- `division_id` foreign key -> `divisions.id`
- `title` string
- `description` text nullable
- `category` string nullable
- `priority` string
- `status` string
- `owner_employee_id` foreign key nullable -> `employees.id`
- `planned_start_date` date nullable
- `due_date` date nullable
- `completed_date` date nullable
- `progress_pct` integer default 0
- `created_at`
- `updated_at`

Status recommended:

- `Not Started`
- `In Progress`
- `Blocked`
- `On Hold`
- `Done`

### 10.5 `work_item_assignees`

Tujuan: mendukung task yang dikerjakan lebih dari satu orang.

Kolom yang disarankan:

- `id` UUID / integer primary key
- `work_item_id` foreign key -> `work_items.id`
- `employee_id` foreign key -> `employees.id`
- `assignment_role` string nullable
- `allocation_pct` integer nullable
- `created_at`

### 10.6 `activity_logs`

Tujuan: menyimpan aktivitas harian / periodik karyawan.

Kolom yang disarankan:

- `id` UUID / integer primary key
- `activity_date` date
- `employee_id` foreign key -> `employees.id`
- `work_item_id` foreign key nullable -> `work_items.id`
- `project_id` foreign key nullable -> `projects.id`
- `activity_type` string
- `summary` text
- `details` text nullable
- `hours_spent` numeric nullable
- `status` string
- `progress_pct` integer nullable
- `blocker_note` text nullable
- `next_action` text nullable
- `created_by` string nullable
- `created_at`
- `updated_at`

Catatan desain:

- `activity_logs` adalah fakta utama untuk analytics.
- `status` di sini adalah status saat aktivitas dicatat, bukan pengganti status master `work_items`.

### 10.7 `status_history`

Tujuan: menyimpan riwayat perubahan status penting.

Kolom yang disarankan:

- `id` UUID / integer primary key
- `entity_type` string
- `entity_id` string / integer
- `old_status` string nullable
- `new_status` string
- `changed_by` string nullable
- `changed_at`
- `note` text nullable

Entity type awal yang didukung:

- `project`
- `work_item`
- `activity_log`

## 11. Dashboard Pages yang Direkomendasikan

### 11.1 Executive Overview

Komponen:

- total employees aktif
- total active projects
- total open work items
- task by status
- blocked task by division
- overdue task list

### 11.2 Division Performance

Komponen:

- filter per divisi
- jumlah task per status
- progress rata-rata per divisi
- anggota divisi dengan workload tertinggi
- trend aktivitas 7/30 hari

### 11.3 Employee Activity

Komponen:

- filter per employee
- log aktivitas terbaru
- workload summary
- total hours / total activity entries
- task yang sedang dikerjakan

### 11.4 Project / Initiative Monitor

Komponen:

- filter per project
- daftar work item
- progress vs due date
- blocked items
- ownership per divisi

### 11.5 Admin Panel

Menu yang dibutuhkan:

- manage divisions
- manage employees
- manage projects
- manage work items
- manage activity logs
- import CSV

## 12. Alur Kerja Aplikasi

Alur minimal yang masuk akal:

1. Admin input master data divisi dan karyawan.
2. Admin input project/inisiatif.
3. Admin input work item dan assign ke employee.
4. Admin atau operator mengisi activity log harian/mingguan.
5. Admin update status task bila ada perubahan.
6. Dashboard otomatis merekap kondisi terbaru.

## 13. Aturan Bisnis Awal

Supaya data konsisten, aturan awal yang direkomendasikan:

- `progress_pct` harus 0-100.
- Jika `status = Done`, maka `completed_date` wajib terisi pada `work_items`.
- Jika `status = Blocked`, maka `blocker_note` sebaiknya wajib pada `activity_logs`.
- Satu employee boleh punya banyak activity log per hari.
- Satu work item boleh punya banyak assignee.
- Work item overdue = `due_date < today` dan status bukan `Done`.

## 14. Desain UI yang Disarankan

Karena targetnya tool internal, desain UI sebaiknya:

- clean dan cepat dibaca
- filter ada di sidebar
- metric cards di bagian atas
- tabel detail di bagian bawah
- warna status konsisten:
  - hijau: `Done`
  - biru: `In Progress`
  - kuning/oranye: `On Hold`
  - merah: `Blocked`
  - abu-abu: `Not Started`

## 15. Struktur Project yang Disarankan

Contoh struktur awal:

```text
productivity-tracker/
├── app/
│   ├── main.py
│   ├── db/
│   │   ├── base.py
│   │   ├── models.py
│   │   ├── session.py
│   │   └── seed.py
│   ├── services/
│   │   ├── dashboard_service.py
│   │   ├── employee_service.py
│   │   └── activity_service.py
│   ├── pages/
│   │   ├── overview.py
│   │   ├── divisions.py
│   │   ├── employees.py
│   │   ├── projects.py
│   │   ├── work_items.py
│   │   └── admin.py
│   └── components/
│       ├── filters.py
│       ├── metrics.py
│       └── tables.py
├── docs/
│   └── employee-activity-dashboard-plan.md
├── data/
│   └── tracker.db
└── pyproject.toml
```

## 16. Fase Implementasi

### Phase 1 - Foundation

- setup app skeleton
- setup SQLite + SQLAlchemy models
- buat seed data dummy
- buat halaman overview sederhana

Output:

- aplikasi jalan lokal
- schema database terbentuk
- ada sample dashboard

### Phase 2 - Admin CRUD

- form master data divisi
- form employee
- form project
- form work item
- form activity log

Output:

- admin bisa input dan edit data langsung dari UI

### Phase 3 - Analytics Dashboard

- division dashboard
- employee dashboard
- project dashboard
- overdue and blocker views

Output:

- stakeholder bisa baca status kerja lintas divisi

### Phase 4 - Data Import & Quality

- upload CSV
- validasi basic
- duplicate checks
- status history logging

Output:

- input data lebih cepat
- kualitas data lebih terjaga

## 17. Risiko dan Trade-off

Trade-off dari pendekatan ini:

- `SQLite` mudah dipakai tapi tidak ideal untuk banyak concurrent writer.
- Tanpa auth proper, aplikasi cocok untuk internal trusted environment saja.
- Streamlit cepat dibangun, tapi fleksibilitas UI dan workflow kompleks lebih terbatas dibanding web app penuh.

Tetap masuk akal karena kebutuhan saat ini adalah proof-of-value dan operasional lokal, bukan SaaS production platform.

## 18. Backlog Setelah V1

Kalau aplikasi terbukti berguna, fase berikutnya bisa:

- migrasi ke `PostgreSQL`
- tambah login sederhana
- tambah role `Admin`, `Manager`, `Viewer`
- auto reminder untuk activity yang belum diisi
- export PDF / Excel
- audit trail yang lebih lengkap
- integrasi ke HR data source atau project management tools

## 19. Rekomendasi Eksekusi Praktis

Urutan kerja yang paling aman:

1. Finalkan schema database dulu.
2. Buat dummy data lintas 3-5 divisi.
3. Bangun halaman overview dan admin CRUD dasar.
4. Tunjukkan ke boss untuk validasi metrik dan tampilan.
5. Baru tambahkan halaman detail dan import CSV.

## 20. Kesimpulan

Solusi terbaik untuk konteks ini bukan backend enterprise, tetapi internal analytics app yang:

- database-nya proper
- schema-nya jelas
- UI dashboard-nya berguna
- admin bisa input dan edit data
- bisa dijalankan lokal dengan effort rendah

Dengan pendekatan ini, kamu tetap deliver sesuatu yang terlihat profesional dan terstruktur, tanpa terjebak membangun infrastruktur backend yang sebenarnya belum dibutuhkan.
